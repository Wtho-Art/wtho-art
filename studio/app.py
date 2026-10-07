"""Local studio for wtho.art. Binds to 127.0.0.1 and publishes with git push."""

from __future__ import annotations

import hmac
import subprocess
import sys
import threading
import time
from datetime import timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from flask import (
    Flask,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

import auth
import content
import gitpublish
import images

OPEN = {"login", "static", "icon"}
HERE = Path(__file__).resolve().parent
DEFAULT_SITE = HERE.parent


def create_app(site_root: Path, auth_dir: Path, preview_origin: str = "http://127.0.0.1:8788", git_runner=None, ssh_check=None) -> Flask:
    app = Flask(
        __name__,
        root_path=str(HERE),
        template_folder="templates",
        static_folder="static",
    )
    app.config.update(
        SITE_ROOT=Path(site_root),
        AUTH_DIR=Path(auth_dir),
        PREVIEW_ORIGIN=preview_origin,
        SECRET_KEY=auth.secret_key(Path(auth_dir)),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=False,
        SESSION_COOKIE_NAME="wtho_studio",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        TEMPLATES_AUTO_RELOAD=True,
        MAX_CONTENT_LENGTH=42 * 1024 * 1024,
        GIT_RUNNER=git_runner or gitpublish.run_git,
        SSH_CHECK=ssh_check or gitpublish.check_github_ssh,
    )

    @app.context_processor
    def inject():
        report = {"allowed": []}
        try:
            report = gitpublish.inspect_status(Path(app.config["SITE_ROOT"]), app.config["GIT_RUNNER"])
        except Exception:
            report = {"allowed": []}
        return {
            "csrf": session.get("csrf", ""),
            "preview_origin": app.config["PREVIEW_ORIGIN"],
            "change_count": len(report.get("allowed") or []),
        }

    @app.before_request
    def protect():
        if "csrf" not in session:
            session["csrf"] = _token()
        if request.method == "POST" and not _tokens_match(
            request.form.get("csrf") or request.headers.get("X-CSRF") or "",
            session.get("csrf") or "",
        ):
            abort(400)
        if request.endpoint in OPEN or request.endpoint is None:
            return None
        if not session.get("admin"):
            return redirect(url_for("login", next=request.path))
        return None

    @app.after_request
    def no_store(response):
        content_type = response.content_type or ""
        if content_type.startswith("text/html"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/favicon.svg")
    def icon():
        return send_file(Path(app.config["SITE_ROOT"]) / "favicon.svg")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("admin"):
            return redirect(_safe_next(request.args.get("next")))
        if request.method == "POST":
            password = request.form.get("password") or ""
            if auth.verify_password(Path(app.config["AUTH_DIR"]), password):
                session.clear()
                session["csrf"] = _token()
                session["admin"] = True
                session.permanent = True
                return redirect(_safe_next(request.form.get("next")))
            time.sleep(0.4)
            flash("Das Passwort stimmt nicht.", "error")
        return render_template("login.html", next_path=request.args.get("next") or "")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    def home():
        return redirect(url_for("works_list"))

    @app.get("/werke")
    def works_list():
        root = _root()
        works = content.load_works(root)
        site = content.load_site(root)
        return render_template("works.html", works=works, hero_id=site.get("heroWorkId") or "")

    @app.post("/werke/reihenfolge")
    def works_reorder():
        try:
            content.reorder_works(_root(), request.form.getlist("id"))
        except content.ContentError as exc:
            flash(str(exc), "error")
            return redirect(url_for("works_list"))
        flash("Reihenfolge gespeichert. Noch nicht veröffentlicht.")
        return redirect(url_for("works_list"))

    @app.post("/werke/startbild")
    def works_hero():
        try:
            content.set_hero(_root(), request.form.get("id") or "")
        except content.ContentError as exc:
            flash(str(exc), "error")
        else:
            flash("Startbild gespeichert. Noch nicht veröffentlicht.")
        return redirect(url_for("works_list"))

    @app.route("/werke/neu", methods=["GET", "POST"])
    def work_new():
        work = content.blank_work()
        if request.method == "POST":
            try:
                work = content.new_work_from_form(content.load_works(_root()), request.form)
                content.upsert_work(_root(), work)
            except content.ContentError as exc:
                flash(str(exc), "error")
                work = _work_from_post()
                return render_template("work.html", work=work, creating=True), 400
            flash("Werk angelegt. Jetzt ein Bild hochladen. Noch nicht veröffentlicht.")
            return redirect(url_for("work_edit", work_id=work["id"]))
        return render_template("work.html", work=work, creating=True)

    @app.route("/werke/<work_id>", methods=["GET", "POST"])
    def work_edit(work_id):
        work = _load_work(work_id)
        if request.method == "POST":
            try:
                content.apply_work_fields(work, request.form)
                content.upsert_work(_root(), work)
            except content.ContentError as exc:
                flash(str(exc), "error")
                return render_template("work.html", work=work, creating=False), 400
            flash("Gespeichert. Noch nicht veröffentlicht.")
            return redirect(url_for("work_edit", work_id=work_id))
        return render_template("work.html", work=work, creating=False)

    @app.post("/werke/<work_id>/bilder")
    def work_upload(work_id):
        work = _load_work(work_id)
        saved = 0
        for storage in request.files.getlist("image"):
            if not storage or not storage.filename:
                continue
            try:
                jpeg = images.prepare_jpeg(storage.read())
                content.add_jpeg(_root(), work, jpeg)
                work = _load_work(work_id)
                saved += 1
            except (images.ImageError, content.ContentError) as exc:
                flash(f"{storage.filename}: {exc}", "error")
        if saved:
            flash(f"{saved} Bild(er) gespeichert. Noch nicht veröffentlicht.")
        return redirect(url_for("work_edit", work_id=work_id))

    @app.post("/werke/<work_id>/bilder/reihenfolge")
    def work_image_order(work_id):
        work = _load_work(work_id)
        try:
            content.reorder_images(_root(), work, request.form.getlist("image"))
        except content.ContentError as exc:
            flash(str(exc), "error")
        else:
            flash("Bilder neu sortiert. Noch nicht veröffentlicht.")
        return redirect(url_for("work_edit", work_id=work_id))

    @app.post("/werke/<work_id>/bilder/entfernen")
    def work_image_delete(work_id):
        work = _load_work(work_id)
        try:
            content.remove_image(_root(), work, request.form.get("name") or "")
        except content.ContentError as exc:
            flash(str(exc), "error")
        else:
            flash("Bild entfernt. Noch nicht veröffentlicht.")
        return redirect(url_for("work_edit", work_id=work_id))

    @app.post("/werke/<work_id>/loeschen")
    def work_delete(work_id):
        if request.form.get("confirm") != "yes":
            flash("Zum Löschen die Bestätigung ankreuzen.", "error")
            return redirect(url_for("work_edit", work_id=work_id))
        try:
            content.delete_work(_root(), work_id)
        except content.ContentError as exc:
            flash(str(exc), "error")
            return redirect(url_for("works_list"))
        flash("Werk entfernt. Noch nicht veröffentlicht.")
        return redirect(url_for("works_list"))

    @app.route("/texte", methods=["GET", "POST"])
    def texts():
        root = _root()
        site = content.load_site(root)
        if request.method == "POST":
            try:
                content.apply_copy(site, request.form)
                content.save_site(root, site)
                content.rebuild_llms(root, content.load_works(root), site)
            except content.ContentError as exc:
                flash(str(exc), "error")
                return render_template("texts.html", site=site, groups=content.copy_groups(site)), 400
            flash("Texte gespeichert. Noch nicht veröffentlicht.")
            return redirect(url_for("texts"))
        return render_template("texts.html", site=site, groups=content.copy_groups(site))

    @app.route("/ausstellungen", methods=["GET", "POST"])
    def lists():
        root = _root()
        site = content.load_site(root)
        if request.method == "POST":
            try:
                content.apply_lists(site, request.form)
                content.save_site(root, site)
            except content.ContentError as exc:
                flash(str(exc), "error")
                return render_template("lists.html", site=site), 400
            flash("Gespeichert. Noch nicht veröffentlicht.")
            return redirect(url_for("lists"))
        return render_template("lists.html", site=site)

    @app.route("/bilder", methods=["GET"])
    def photos():
        return render_template("photos.html", places=_place_rows())

    @app.route("/bilder/<place_id>", methods=["GET", "POST"])
    def place_edit(place_id):
        place = _load_place(place_id)
        if request.method == "POST":
            try:
                content.apply_place_fields(place, request.form)
                content.upsert_place(_root(), place)
            except content.ContentError as exc:
                flash(str(exc), "error")
                return render_template("place.html", place=place), 400
            flash("Gespeichert. Noch nicht veröffentlicht.")
            return redirect(url_for("place_edit", place_id=place_id))
        return render_template("place.html", place=place)

    @app.post("/bilder/<place_id>/bilder")
    def place_upload(place_id):
        place = _load_place(place_id)
        saved = 0
        for storage in request.files.getlist("image"):
            if not storage or not storage.filename:
                continue
            try:
                jpeg = images.prepare_jpeg(storage.read())
                content.add_place_jpeg(_root(), place, jpeg)
                place = _load_place(place_id)
                saved += 1
            except (images.ImageError, content.ContentError) as exc:
                flash(f"{storage.filename}: {exc}", "error")
        if saved:
            flash(f"{saved} Bild(er) gespeichert. Noch nicht veröffentlicht.")
        return redirect(url_for("place_edit", place_id=place_id))

    @app.post("/bilder/<place_id>/bilder/reihenfolge")
    def place_image_order(place_id):
        place = _load_place(place_id)
        try:
            content.reorder_place_images(_root(), place, request.form.getlist("image"))
        except content.ContentError as exc:
            flash(str(exc), "error")
        else:
            flash("Bilder neu sortiert. Noch nicht veröffentlicht.")
        return redirect(url_for("place_edit", place_id=place_id))

    @app.post("/bilder/<place_id>/bilder/entfernen")
    def place_image_delete(place_id):
        place = _load_place(place_id)
        try:
            content.remove_place_image(_root(), place, request.form.get("name") or "")
        except content.ContentError as exc:
            flash(str(exc), "error")
        else:
            flash("Bild entfernt. Noch nicht veröffentlicht.")
        return redirect(url_for("place_edit", place_id=place_id))

    @app.route("/veroeffentlichen", methods=["GET", "POST"])
    def publish():
        root = _root()
        report = gitpublish.inspect_status(root, current_app.config["GIT_RUNNER"])
        ssh_ok, ssh_message = _ssh_status()
        account = gitpublish.github_account(ssh_message)
        author = _identity()
        if request.method == "POST":
            if not ssh_ok:
                flash(ssh_message, "error")
                return redirect(url_for("publish"))
            try:
                result = gitpublish.publish(
                    root,
                    request.form.get("message") or "",
                    runner=current_app.config["GIT_RUNNER"],
                    ssh_ok=ssh_ok,
                )
            except gitpublish.GitError as exc:
                flash(str(exc), "error")
                if exc.output and exc.output != str(exc):
                    flash(exc.output, "error")
                return redirect(url_for("publish"))
            flash("Veröffentlicht. GitHub Pages braucht meist eine Minute.")
            if result["blocked"]:
                flash("Nicht mitgeschickt: " + ", ".join(result["blocked"]), "error")
            return redirect(url_for("publish"))
        return render_template(
            "publish.html",
            report=report,
            ssh_ok=ssh_ok,
            ssh_message=ssh_message,
            account=account,
            author=author,
        )

    @app.route("/konto", methods=["GET", "POST"])
    def password():
        if request.method == "POST":
            directory = Path(app.config["AUTH_DIR"])
            current = request.form.get("current") or ""
            new = request.form.get("new") or ""
            again = request.form.get("again") or ""
            if not auth.verify_password(directory, current):
                flash("Das bisherige Passwort stimmt nicht.", "error")
            elif new != again:
                flash("Die neuen Passwörter sind verschieden.", "error")
            else:
                try:
                    auth.set_password(directory, new)
                except ValueError as exc:
                    flash(str(exc), "error")
                else:
                    flash("Passwort geändert.")
                    return redirect(url_for("password"))
        return render_template("password.html")

    @app.get("/media/<path:relpath>")
    def media(relpath):
        root = Path(app.config["SITE_ROOT"]).resolve()
        rel = Path(relpath)
        if rel.is_absolute() or ".." in rel.parts or not rel.parts or rel.parts[0] not in {"works", "images"}:
            abort(404)
        full = (root / rel).resolve()
        if root not in full.parents or not full.is_file():
            abort(404)
        response = send_file(full)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(400)
    def bad_request(_exc):
        return render_template("error.html", message="Das Formular ist abgelaufen. Bitte erneut versuchen."), 400

    @app.errorhandler(404)
    def missing(_exc):
        return render_template("error.html", message="Diese Seite gibt es nicht."), 404

    @app.errorhandler(413)
    def too_large(_exc):
        flash("Die Datei ist größer als 40 MB.", "error")
        return redirect(request.referrer or url_for("works_list"))

    return app


def _root() -> Path:
    return Path(current_app.config["SITE_ROOT"])


def _token() -> str:
    import secrets

    return secrets.token_urlsafe(32)


def _tokens_match(sent: str, expected: str) -> bool:
    if not sent or not expected or len(sent) != len(expected):
        return False
    return hmac.compare_digest(sent, expected)


def _safe_next(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return url_for("works_list")


def _load_work(work_id: str) -> dict:
    if not content.ID_RE.fullmatch(work_id or ""):
        abort(404)
    work = content.find_work(content.load_works(_root()), work_id)
    if work is None:
        abort(404)
    return work


def _work_from_post() -> dict:
    work = content.blank_work()
    try:
        content.apply_work_fields(work, request.form)
    except content.ContentError:
        work["title"]["de"] = request.form.get("title_de", "")
        work["title"]["en"] = request.form.get("title_en", "")
        work["medium"]["de"] = request.form.get("medium_de", "")
        work["medium"]["en"] = request.form.get("medium_en", "")
        work["statement"]["de"] = request.form.get("statement_de", "")
        work["statement"]["en"] = request.form.get("statement_en", "")
        work["year"] = request.form.get("year", "")
        work["size"] = request.form.get("size", "")
        work["layout"] = request.form.get("layout") or "portrait"
        work["span"] = request.form.get("span") == "yes"
    return work


def _load_place(place_id: str) -> dict:
    place = content.find_place(content.load_site(_root()), place_id)
    if not place:
        abort(404)
    return place


def _place_rows() -> list[dict]:
    root = _root()
    rows = []
    for place in content.load_site(root).get("places") or []:
        if place.get("id") not in content.PLACE_IDS:
            continue
        images_ = list(place.get("images") or [])
        cover = images_[0] if images_ else ""
        path = root / "images" / place["id"] / cover if cover else None
        rows.append(
            {
                "id": place["id"],
                "title": place.get("title") or {},
                "cover": cover,
                "count": len(images_),
                "exists": bool(path and path.is_file()),
            }
        )
    return rows


def _ssh_status() -> tuple[bool, str]:
    cache = current_app.extensions.setdefault("ssh_cache", {"at": 0, "ok": False, "message": ""})
    now = time.time()
    if now - cache["at"] < 30:
        return cache["ok"], cache["message"]
    ok, message = current_app.config["SSH_CHECK"]()
    cache.update(at=now, ok=ok, message=message)
    return ok, message


def _identity() -> tuple[str, str]:
    try:
        return gitpublish.read_identity(_root())
    except gitpublish.GitError:
        return ("", "")


def _preview_handler(directory: str):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def list_directory(self, path):
            self.send_error(404)
            return None

        def translate_path(self, path):
            raw = urlparse(path).path
            if raw == "/studio" or raw.startswith("/studio/"):
                return str(Path(directory) / ".__no_studio__")
            return super().translate_path(path)

        def log_message(self, fmt, *args):
            sys.stderr.write("preview " + (fmt % args) + "\n")

    return Handler


def start_preview(directory: Path, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", port), _preview_handler(str(directory)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def main() -> None:
    site = DEFAULT_SITE
    port = 8787
    preview_port = 8788
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=site, capture_output=True, text=True)
    if top.returncode != 0 or Path(top.stdout.strip()).resolve() != site.resolve():
        sys.exit("Dieser Ordner ist nicht das Git-Repository der Website.")
    gitpublish.ensure_identity(site)
    auth_dir = HERE / ".auth"
    new_password = auth.ensure_auth(auth_dir)
    app = create_app(site, auth_dir, preview_origin=f"http://127.0.0.1:{preview_port}")
    try:
        start_preview(site, preview_port)
    except OSError as exc:
        sys.exit(f"Vorschau-Port {preview_port} ist belegt: {exc}")
    print(f"Atelier:  http://127.0.0.1:{port}/")
    print(f"Vorschau: http://127.0.0.1:{preview_port}/")
    if new_password:
        print()
        print("Erstes Passwort (bitte notieren):")
        print(new_password)
        print()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
