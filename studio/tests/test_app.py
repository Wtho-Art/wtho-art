import io
import json
import re
import shutil
from pathlib import Path

from PIL import Image

import auth
import content
from app import create_app

REPO = Path(__file__).resolve().parents[2]
PASSWORD = "test-password"


def _csrf(html: str) -> str:
    match = re.search(r'name="csrf" value="([^"]+)"', html)
    assert match, html[:500]
    return match.group(1)


def _site(tmp_path):
    root = tmp_path / "site"
    (root / "data").mkdir(parents=True)
    (root / "works" / "touched").mkdir(parents=True)
    (root / "images").mkdir()
    shutil.copy(REPO / "data" / "works.json", root / "data" / "works.json")
    shutil.copy(REPO / "data" / "site.json", root / "data" / "site.json")
    shutil.copy(REPO / "llms.txt", root / "llms.txt")
    shutil.copy(REPO / "sitemap.xml", root / "sitemap.xml")
    shutil.copy(REPO / "works" / "touched" / "index.html", root / "works" / "touched" / "index.html")
    shutil.copy(REPO / "favicon.svg", root / "favicon.svg")
    auth_dir = tmp_path / "auth"
    auth_dir.mkdir()
    (auth_dir / "secret.key").write_bytes(b"k" * 32)
    auth.set_password(auth_dir, PASSWORD)
    calls = []

    def runner(args, root_arg):
        calls.append(list(args))
        if args[1] == "status":
            return " M data/site.json\n M index.html\n"
        if args[:3] == ["git", "diff", "--cached"]:
            return "data/site.json\n"
        if args[1] == "config" and args[2] == "user.name":
            return "Thorsten Weitz\n"
        if args[1] == "config" and args[2] == "user.email":
            return "Wtho.Art@proton.me\n"
        return ""

    app = create_app(
        root,
        auth_dir,
        git_runner=runner,
        ssh_check=lambda: (True, "Hi Wtho-Art! You've successfully authenticated."),
    )
    app.config["TESTING"] = True
    return app.test_client(), root, calls


def _login(client):
    page = client.get("/login")
    token = _csrf(page.get_data(as_text=True))
    response = client.post("/login", data={"csrf": token, "password": PASSWORD}, follow_redirects=True)
    assert response.status_code == 200
    return token


def test_place_page_saves_text(tmp_path):
    client, root, _calls = _site(tmp_path)
    _login(client)
    assert client.get("/bilder/missing").status_code == 404
    page = client.get("/bilder/portrait")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Porträt im Atelier Freiburg" in html
    response = client.post(
        "/bilder/portrait",
        data={
            "csrf": _csrf(html),
            "title_de": "Porträt",
            "title_en": "Portrait",
            "text_de": "Neuer Platzhalter.",
            "text_en": "New placeholder.",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    site = json.loads((root / "data" / "site.json").read_text(encoding="utf-8"))
    place = next(item for item in site["places"] if item["id"] == "portrait")
    assert place["text"]["de"] == "Neuer Platzhalter."
    assert "Neuer Platzhalter." in (root / "images" / "portrait" / "index.html").read_text(encoding="utf-8")
    assert "https://wtho.art/images/portrait/" in (root / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://wtho.art/images/atelier/" in (root / "sitemap.xml").read_text(encoding="utf-8")


def test_login_wall_and_bad_csrf(tmp_path):
    client, _root, _calls = _site(tmp_path)
    assert client.get("/werke", follow_redirects=False).status_code == 302
    assert client.post("/login", data={"password": PASSWORD}).status_code == 400


def test_edit_reorder_upload_and_publish_stays_local_until_post(tmp_path):
    client, root, calls = _site(tmp_path)
    _login(client)
    page = client.get("/veroeffentlichen")
    assert b"git push" not in b"\n".join(b" ".join(c).encode() for c in calls if c[1:2] == ["push"])
    assert "Veröffentlichen" in page.get_data(as_text=True)
    assert not any(command[1] == "push" for command in calls)

    edit = client.get("/werke/touched")
    html = edit.get_data(as_text=True)
    token = _csrf(html)
    assert "Violett und Blau" in html
    response = client.post(
        "/werke/touched",
        data={
            "csrf": token,
            "title_de": "The raw power and sensitivity - Touched",
            "title_en": "The raw power and sensitivity - Touched",
            "year": "2026",
            "size": "100 × 70 cm",
            "medium_de": "Öl auf Leinwand",
            "medium_en": "Oil on canvas",
            "statement_de": "Ein neuer Satz für die Probe.",
            "statement_en": "A new sentence for the test.",
            "layout": "portrait",
            "span": "yes",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    saved = json.loads((root / "data" / "works.json").read_text(encoding="utf-8"))
    touched = next(work for work in saved if work["id"] == "touched")
    assert touched["statement"]["de"] == "Ein neuer Satz für die Probe."
    page_html = (root / "works" / "touched" / "index.html").read_text(encoding="utf-8")
    assert "Ein neuer Satz für die Probe." in page_html
    assert "--rupture" in page_html

    works = client.get("/werke").get_data(as_text=True)
    order_form = re.search(r'id="order-form".*?</form>', works, re.S).group(0)
    ids = re.findall(r'name="id" value="([^"]+)"', order_form)
    assert ids[0] == "touched"
    token = _csrf(works)
    flipped = list(reversed(ids))
    client.post("/werke/reihenfolge", data={"csrf": token, "id": flipped}, follow_redirects=True)
    ordered = [work["id"] for work in json.loads((root / "data" / "works.json").read_text(encoding="utf-8"))]
    assert ordered == flipped

    token = _csrf(client.get("/werke/neu").get_data(as_text=True))
    created = client.post(
        "/werke/neu",
        data={
            "csrf": token,
            "title_de": "Probe",
            "title_en": "Studio Probe",
            "year": "2026",
            "size": "10 × 10 cm",
            "medium_de": "Öl",
            "medium_en": "Oil",
            "statement_de": "Nur eine Probe.",
            "statement_en": "Only a test.",
            "layout": "landscape",
        },
        follow_redirects=True,
    )
    assert created.status_code == 200
    assert (root / "works" / "studio-probe" / "index.html").is_file()

    buffer = io.BytesIO()
    Image.new("RGB", (3000, 1000), (10, 20, 30)).save(buffer, format="PNG")
    token = _csrf(created.get_data(as_text=True))
    uploaded = client.post(
        "/werke/studio-probe/bilder",
        data={"csrf": token, "image": (io.BytesIO(buffer.getvalue()), "probe.png")},
        follow_redirects=True,
    )
    assert uploaded.status_code == 200
    jpeg = root / "works" / "studio-probe" / "studio-probe.jpg"
    assert jpeg.is_file()
    assert jpeg.read_bytes().startswith(b"\xff\xd8")
    with Image.open(jpeg) as photo:
        assert photo.size[0] == 2000

    before = len(calls)
    token = _csrf(client.get("/veroeffentlichen").get_data(as_text=True))
    published = client.post(
        "/veroeffentlichen",
        data={"csrf": token, "message": "Probe, nicht wirklich gepusht"},
        follow_redirects=True,
    )
    assert published.status_code == 200
    assert "Veröffentlicht" in published.get_data(as_text=True)
    pushes = [command for command in calls[before:] if command[1:2] == ["push"]]
    assert pushes == [["git", "push", "origin", "main"]]
