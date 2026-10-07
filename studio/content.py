"""Read and write the site JSON, work pages, sitemap, and llms.txt."""

from __future__ import annotations

import json
import re
import secrets
import shutil
import unicodedata
from pathlib import Path

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FALLBACK_PAGE = Path(__file__).resolve().parent / "fallback_work.html"
FALLBACK_PLACE = Path(__file__).resolve().parent / "fallback_place.html"
MAX_IMAGES = 12

COPY_GROUPS: list[tuple[str, list[tuple[str, str, bool]]]] = [
    (
        "Navigation",
        [
            ("skip", "Sprunglink", False),
            ("navWorks", "Menü: Werke", False),
            ("navAbout", "Menü: Künstler/Atelier", False),
            ("navExhibitions", "Menü: Ausstellungen", False),
            ("navNewsletter", "Menü: Newsletter", False),
            ("navContact", "Menü: Kontakt", False),
            ("navPrivacy", "Menü: Datenschutz", False),
            ("navImprint", "Menü: Impressum", False),
        ],
    ),
    (
        "Hero",
        [
            ("kicker", "Zeile über dem Namen", False),
            ("heroQuote", "Satz", True),
            ("heroLead", "Einleitung", True),
            ("ctaWorks", "Schaltfläche Werke", False),
            ("ctaContact", "Schaltfläche Anfrage", False),
        ],
    ),
    (
        "Manifest",
        [
            ("manifestoTitle", "Überschrift", False),
            ("manifestoBody", "Text", True),
        ],
    ),
    (
        "Galerie",
        [
            ("worksKicker", "Kleine Überschrift", False),
            ("worksTitle", "Überschrift", False),
            ("worksLead", "Einleitung", True),
            ("inquire", "Schaltfläche auf der Werkseite", False),
            ("worksBack", "Zurück-Link auf der Werkseite", False),
        ],
    ),
    (
        "Künstler",
        [
            ("aboutKicker", "Kleine Überschrift", False),
            ("aboutTitle", "Überschrift", False),
            ("aboutP1", "Absatz 1", True),
            ("aboutP2", "Absatz 2", True),
            ("aboutP3", "Absatz 3", True),
            ("aboutP4", "Absatz 4", True),
            ("aboutQuote", "Zitat", True),
            ("pathTitle", "Überschrift Werdegang", False),
        ],
    ),
    (
        "Ausstellungen",
        [
            ("exhibitionsKicker", "Kleine Überschrift", False),
            ("exhibitionsTitle", "Überschrift", False),
        ],
    ),
    (
        "Newsletter",
        [
            ("newsletterKicker", "Kleine Überschrift", False),
            ("newsletterTitle", "Überschrift", False),
            ("newsletterLead", "Einleitung", True),
            ("newsletterEmail", "Feld E-Mail", False),
            ("newsletterConsent", "Einwilligung", True),
            ("newsletterSubmit", "Schaltfläche", False),
            ("newsletterNote", "Hinweis", True),
            ("newsletterError", "Fehlermeldung", True),
            ("newsletterSuccess", "Erfolgsmeldung", False),
        ],
    ),
    (
        "Kontakt",
        [
            ("contactKicker", "Kleine Überschrift", False),
            ("contactTitle", "Überschrift", False),
            ("contactLead", "Einleitung", True),
            ("contactName", "Feld Name", False),
            ("contactEmail", "Feld E-Mail", False),
            ("contactWork", "Feld Werk", False),
            ("contactWorkPlaceholder", "Platzhalter Werk", False),
            ("contactMessage", "Feld Nachricht", False),
            ("contactSend", "Schaltfläche", False),
            ("contactNote", "Hinweis", True),
            ("instagram", "Beschriftung Instagram", False),
            ("formSent", "Meldung gesendet", False),
            ("formFallback", "Meldung E-Mail-Programm", False),
        ],
    ),
    (
        "Fußzeile",
        [
            ("footerStudio", "Atelier", False),
            ("footerRights", "Rechte", False),
        ],
    ),
]

PLACE_IDS = ("portrait", "atelier")


class ContentError(Exception):
    pass


def dumps_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


def load_works(root: Path) -> list:
    return load_json(root / "data" / "works.json")


def save_works(root: Path, works: list) -> None:
    write_text(root / "data" / "works.json", dumps_json(works))


def load_site(root: Path) -> dict:
    return load_json(root / "data" / "site.json")


def save_site(root: Path, site: dict) -> None:
    write_text(root / "data" / "site.json", dumps_json(site))


def slugify(text: str) -> str:
    text = text.replace("ß", "ss").replace("ẞ", "SS")
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    text = text[:60].strip("-")
    return text or "werk"


def unique_id(works: list, slug: str) -> str:
    taken = {work["id"] for work in works}
    if slug not in taken:
        return slug
    number = 2
    while f"{slug}-{number}" in taken:
        number += 1
    return f"{slug}-{number}"


def find_work(works: list, work_id: str) -> dict | None:
    for work in works:
        if work.get("id") == work_id:
            return work
    return None


def work_folder(root: Path, work_id: str) -> Path:
    if not ID_RE.fullmatch(work_id or ""):
        raise ContentError("Die Werk-ID ist ungültig.")
    root = root.resolve()
    folder = (root / "works" / work_id).resolve()
    works_dir = (root / "works").resolve()
    if folder.parent != works_dir:
        raise ContentError("Die Werk-ID ist ungültig.")
    return folder


def apply_work_fields(work: dict, form) -> dict:
    title_de = form.get("title_de", "").strip()
    title_en = form.get("title_en", "").strip()
    medium_de = form.get("medium_de", "").strip()
    medium_en = form.get("medium_en", "").strip()
    year = form.get("year", "").strip()
    if not title_de or not title_en:
        raise ContentError("Titel auf Deutsch und Englisch eintragen.")
    if not year:
        raise ContentError("Jahr eintragen.")
    if not medium_de or not medium_en:
        raise ContentError("Material auf Deutsch und Englisch eintragen.")
    layout = form.get("layout", "portrait")
    if layout not in {"portrait", "landscape"}:
        raise ContentError("Format ist ungültig.")
    work["year"] = year
    work["size"] = form.get("size", "").strip()
    work["layout"] = layout
    work["span"] = form.get("span") == "yes"
    work.setdefault("title", {})
    work.setdefault("medium", {})
    work.setdefault("statement", {})
    work["title"]["de"] = title_de
    work["title"]["en"] = title_en
    work["medium"]["de"] = medium_de
    work["medium"]["en"] = medium_en
    work["statement"]["de"] = form.get("statement_de", "").strip()
    work["statement"]["en"] = form.get("statement_en", "").strip()
    return work


def blank_work() -> dict:
    return {
        "id": "",
        "year": "",
        "size": "",
        "layout": "portrait",
        "span": False,
        "hero": False,
        "images": [],
        "title": {"de": "", "en": ""},
        "medium": {"de": "", "en": ""},
        "statement": {"de": "", "en": ""},
    }


def new_work_from_form(works: list, form) -> dict:
    work = blank_work()
    apply_work_fields(work, form)
    work["id"] = unique_id(works, slugify(work["title"]["en"]))
    work["hero"] = False
    work["images"] = []
    return work


def upsert_work(root: Path, work: dict) -> list:
    works = load_works(root)
    for index, item in enumerate(works):
        if item["id"] == work["id"]:
            works[index] = work
            break
    else:
        works.append(work)
    save_works(root, works)
    write_work_page(root, work)
    rebuild_sitemap(root, works)
    rebuild_llms(root, works, load_site(root))
    return works


def reorder_works(root: Path, ids: list[str]) -> list:
    works = load_works(root)
    current = [work["id"] for work in works]
    if sorted(ids) != sorted(current) or len(ids) != len(current):
        raise ContentError("Die Werkliste ist unvollständig.")
    by_id = {work["id"]: work for work in works}
    ordered = [by_id[work_id] for work_id in ids]
    save_works(root, ordered)
    rebuild_sitemap(root, ordered)
    rebuild_llms(root, ordered, load_site(root))
    return ordered


def set_hero(root: Path, work_id: str) -> None:
    works = load_works(root)
    if find_work(works, work_id) is None:
        raise ContentError("Dieses Werk gibt es nicht.")
    site = load_site(root)
    site["heroWorkId"] = work_id
    for work in works:
        work["hero"] = work["id"] == work_id
    save_site(root, site)
    save_works(root, works)


def delete_work(root: Path, work_id: str) -> None:
    folder = work_folder(root, work_id)
    works = [work for work in load_works(root) if work["id"] != work_id]
    if len(works) == len(load_works(root)):
        raise ContentError("Dieses Werk gibt es nicht.")
    site = load_site(root)
    if site.get("heroWorkId") == work_id:
        site["heroWorkId"] = works[0]["id"] if works else ""
        for work in works:
            work["hero"] = work["id"] == site["heroWorkId"]
    if folder.is_dir():
        shutil.rmtree(folder)
    save_works(root, works)
    save_site(root, site)
    rebuild_sitemap(root, works)
    rebuild_llms(root, works, site)


def safe_image_name(name: str) -> str:
    if not name or name.startswith(".") or Path(name).name != name:
        raise ContentError("Ungültiger Bildname.")
    return name


def normalize_image_names(folder: Path, work_id: str, names: list[str]) -> list[str]:
    present: list[Path] = []
    for name in names:
        safe_image_name(name)
        source = (folder / name).resolve()
        folder_resolved = folder.resolve()
        if source.parent != folder_resolved or not source.is_file():
            continue
        present.append(source)
    desired = [f"{work_id}.jpg" if index == 0 else f"{work_id}-{index + 1}.jpg" for index in range(len(present))]
    if [path.name for path in present] == desired:
        return desired
    temps = []
    for index, source in enumerate(present):
        temporary = folder / f".rename-{index}-{secrets.token_hex(3)}.jpg"
        source.replace(temporary)
        temps.append(temporary)
    final = []
    for temporary, name in zip(temps, desired):
        temporary.replace(folder / name)
        final.append(name)
    return final


def prune_extra_images(folder: Path, names: list[str]) -> None:
    keep = set(names) | {"index.html"}
    image_suffixes = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    if not folder.is_dir():
        return
    for path in folder.iterdir():
        if path.name.startswith("."):
            if path.is_file():
                path.unlink()
            continue
        if path.is_file() and path.name not in keep and path.suffix.lower() in image_suffixes:
            path.unlink()


def sync_work_images(root: Path, work: dict) -> None:
    folder = work_folder(root, work["id"])
    folder.mkdir(parents=True, exist_ok=True)
    work["images"] = normalize_image_names(folder, work["id"], list(work.get("images") or []))
    prune_extra_images(folder, work["images"])


def add_jpeg(root: Path, work: dict, jpeg: bytes) -> None:
    if len(work.get("images") or []) >= MAX_IMAGES:
        raise ContentError("Höchstens 12 Bilder pro Werk.")
    folder = work_folder(root, work["id"])
    folder.mkdir(parents=True, exist_ok=True)
    name = f"upload-{secrets.token_hex(4)}.jpg"
    write_bytes(folder / name, jpeg)
    work.setdefault("images", []).append(name)
    sync_work_images(root, work)
    upsert_work(root, work)


def remove_image(root: Path, work: dict, name: str) -> None:
    safe_image_name(name)
    images = list(work.get("images") or [])
    if name not in images:
        raise ContentError("Das Bild gehört nicht zu diesem Werk.")
    images.remove(name)
    work["images"] = images
    path = work_folder(root, work["id"]) / name
    if path.is_file():
        path.unlink()
    sync_work_images(root, work)
    upsert_work(root, work)


def reorder_images(root: Path, work: dict, names: list[str]) -> None:
    current = list(work.get("images") or [])
    if names != current and (sorted(names) != sorted(current) or len(names) != len(current)):
        raise ContentError("Die Bilderliste ist unvollständig.")
    if sorted(names) != sorted(current) or len(names) != len(current):
        raise ContentError("Die Bilderliste ist unvollständig.")
    for name in names:
        safe_image_name(name)
    work["images"] = names
    sync_work_images(root, work)
    upsert_work(root, work)


def _sub_once(pattern: str, repl, text: str, slot: str) -> str:
    def call(match):
        return repl(match) if callable(repl) else repl

    updated, count = re.subn(pattern, call, text, count=1, flags=re.S)
    if count != 1:
        raise ContentError(f"Die Werkseite hat kein Feld {slot}.")
    return updated


def _replace_id_text(html: str, element_id: str, value: str) -> str:
    pattern = rf'(id="{re.escape(element_id)}"[^>]*>)(.*?)(</)'
    escaped = _esc(value)
    return _sub_once(pattern, lambda match: match.group(1) + escaped + match.group(3), html, element_id)


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _set_meta(html: str, attr: str, key: str, value: str) -> str:
    escaped = _esc(value)
    pattern = rf'(<meta\b[^>]*\b{attr}="{re.escape(key)}"[^>]*\bcontent=")([^"]*)(")'
    return _sub_once(pattern, lambda match: match.group(1) + escaped + match.group(3), html, f"{attr}:{key}")


def _set_img(html: str, src: str, alt: str) -> str:
    pattern = r'<img\b[^>]*\bid="mainImg"[^>]*/?>'

    def repl(match):
        tag = match.group(0)
        tag = re.sub(r'\bsrc="[^"]*"', f'src="{_esc(src)}"', tag, count=1)
        tag = re.sub(r'\balt="[^"]*"', f'alt="{_esc(alt)}"', tag, count=1)
        return tag

    return _sub_once(pattern, repl, html, "mainImg")


def _set_href(html: str, element_id: str, href: str) -> str:
    pattern = rf'<a\b[^>]*\bid="{re.escape(element_id)}"[^>]*>'

    def repl(match):
        tag = match.group(0)
        updated, count = re.subn(r'\bhref="[^"]*"', f'href="{_esc(href)}"', tag, count=1)
        if count != 1:
            raise ContentError("Die Werkseite hat keinen Anfrage-Link.")
        return updated

    return _sub_once(pattern, repl, html, element_id)


def _dimensions(size: str) -> tuple[str, str]:
    numbers = re.findall(r"\d+(?:[.,]\d+)?", size or "")
    if len(numbers) >= 2:
        return numbers[0].replace(",", "."), numbers[1].replace(",", ".")
    if len(numbers) == 1:
        return numbers[0].replace(",", "."), ""
    return "", ""


def render_work_html(html: str, work: dict) -> str:
    title_de = work["title"]["de"]
    medium_de = work["medium"]["de"]
    medium_en = work["medium"]["en"]
    year = work.get("year") or ""
    size = work.get("size") or ""
    show_size = bool(size) and size != "—"
    page_title = f"{title_de} — wtho.art"
    if show_size:
        description = f"{title_de} — {medium_de}, {size}. Thorsten Weitz, wtho.art."
        og_description = f"{medium_de}, {size}"
        medium_line = f"{medium_de} · {size}"
    else:
        description = f"{title_de} — {medium_de}. Thorsten Weitz, wtho.art."
        og_description = medium_de
        medium_line = medium_de
    image = (work.get("images") or [f"{work['id']}.jpg"])[0]
    canonical = f"https://wtho.art/works/{work['id']}/"
    image_url = f"https://wtho.art/works/{work['id']}/{image}"
    width, height = _dimensions(size if show_size else "")
    payload = {
        "@context": "https://schema.org",
        "@type": "VisualArtwork",
        "name": title_de,
        "creator": {"@type": "Person", "name": "Thorsten Weitz", "url": "https://wtho.art/"},
        "artMedium": medium_en,
        "artform": "Painting",
        "dateCreated": year,
        "image": image_url,
        "url": canonical,
    }
    if width:
        payload["width"] = {"@type": "Distance", "name": f"{width} cm"}
    if height:
        payload["height"] = {"@type": "Distance", "name": f"{height} cm"}
    raw = json.dumps(payload, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    block = '<script type="application/ld+json">\n' + raw + "\n  </script>"

    html = _sub_once(r"<title>.*?</title>", lambda _m: f"<title>{_esc(page_title)}</title>", html, "title")
    html = _set_meta(html, "name", "description", description)
    html = _sub_once(
        r'(<link rel="canonical" href=")([^"]*)(")',
        lambda match: match.group(1) + canonical + match.group(3),
        html,
        "canonical",
    )
    html = _set_meta(html, "property", "og:title", page_title)
    html = _set_meta(html, "property", "og:description", og_description)
    html = _set_meta(html, "property", "og:image", image_url)
    html = _set_meta(html, "property", "og:url", canonical)
    html = _set_meta(html, "name", "twitter:title", page_title)
    html = _set_meta(html, "name", "twitter:image", image_url)
    html = _sub_once(
        r'<script type="application/ld\+json">.*?</script>',
        lambda _m: block,
        html,
        "json-ld",
    )
    html = _set_img(html, image, title_de)
    html = _replace_id_text(html, "metaYear", year)
    html = _replace_id_text(html, "title", title_de)
    html = _replace_id_text(html, "metaMedium", medium_line)
    html = _replace_id_text(html, "statement", work["statement"]["de"])
    html = _set_href(html, "inquire", f"/?work={work['id']}#kontakt")
    return html


def _donor_html(root: Path, work_id: str) -> str:
    own = root / "works" / work_id / "index.html"
    if own.is_file():
        return own.read_text(encoding="utf-8")
    preferred = root / "works" / "touched" / "index.html"
    if preferred.is_file():
        return preferred.read_text(encoding="utf-8")
    found = sorted((root / "works").glob("*/index.html"))
    if found:
        return found[0].read_text(encoding="utf-8")
    if FALLBACK_PAGE.is_file():
        return FALLBACK_PAGE.read_text(encoding="utf-8")
    raise ContentError("Es gibt keine Werkseite als Vorlage.")


def write_work_page(root: Path, work: dict) -> None:
    folder = work_folder(root, work["id"])
    folder.mkdir(parents=True, exist_ok=True)
    html = render_work_html(_donor_html(root, work["id"]), work)
    write_text(folder / "index.html", html)


def find_place(site: dict, place_id: str) -> dict | None:
    if place_id not in PLACE_IDS:
        return None
    for place in site.get("places") or []:
        if place.get("id") == place_id:
            return place
    return None


def place_folder(root: Path, place_id: str) -> Path:
    if place_id not in PLACE_IDS:
        raise ContentError("Diese Seite gibt es nicht.")
    root = root.resolve()
    folder = (root / "images" / place_id).resolve()
    images_dir = (root / "images").resolve()
    if folder.parent != images_dir:
        raise ContentError("Diese Seite gibt es nicht.")
    return folder


def apply_place_fields(place: dict, form) -> dict:
    title_de = form.get("title_de", "").strip()
    title_en = form.get("title_en", "").strip()
    if not title_de or not title_en:
        raise ContentError("Titel auf Deutsch und Englisch eintragen.")
    place.setdefault("title", {})
    place.setdefault("text", {})
    place["title"]["de"] = title_de
    place["title"]["en"] = title_en
    place["text"]["de"] = form.get("text_de", "").strip()
    place["text"]["en"] = form.get("text_en", "").strip()
    return place


def render_place_html(html: str, place: dict) -> str:
    title_de = place["title"]["de"]
    text_de = (place.get("text") or {}).get("de") or ""
    page_title = f"{title_de} — wtho.art"
    description = " ".join((text_de or title_de).split())
    image = (place.get("images") or [f"{place['id']}.jpg"])[0]
    canonical = f"https://wtho.art/images/{place['id']}/"
    image_url = f"https://wtho.art/images/{place['id']}/{image}"
    payload = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title_de,
        "description": description,
        "url": canonical,
        "image": image_url,
        "isPartOf": {"@type": "WebSite", "name": "wtho.art", "url": "https://wtho.art/"},
    }
    raw = json.dumps(payload, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    block = '<script type="application/ld+json">\n' + raw + "\n  </script>"
    html = _sub_once(r"<title>.*?</title>", lambda _m: f"<title>{_esc(page_title)}</title>", html, "title")
    html = _set_meta(html, "name", "description", description)
    html = _sub_once(
        r'(<link rel="canonical" href=")([^"]*)(")',
        lambda match: match.group(1) + canonical + match.group(3),
        html,
        "canonical",
    )
    html = _set_meta(html, "property", "og:title", page_title)
    html = _set_meta(html, "property", "og:description", description)
    html = _set_meta(html, "property", "og:image", image_url)
    html = _set_meta(html, "property", "og:url", canonical)
    html = _set_meta(html, "name", "twitter:title", page_title)
    html = _set_meta(html, "name", "twitter:image", image_url)
    html = _sub_once(
        r'<script type="application/ld\+json">.*?</script>',
        lambda _m: block,
        html,
        "json-ld",
    )
    html = _set_img(html, image, title_de)
    html = _replace_id_text(html, "title", title_de)
    html = _replace_id_text(html, "statement", text_de)
    return html


def _place_donor(root: Path, place_id: str) -> str:
    own = root / "images" / place_id / "index.html"
    if own.is_file():
        return own.read_text(encoding="utf-8")
    if FALLBACK_PLACE.is_file():
        return FALLBACK_PLACE.read_text(encoding="utf-8")
    raise ContentError("Es gibt keine Vorlage für die Bildseite.")


def write_place_page(root: Path, place: dict) -> None:
    folder = place_folder(root, place["id"])
    folder.mkdir(parents=True, exist_ok=True)
    html = render_place_html(_place_donor(root, place["id"]), place)
    write_text(folder / "index.html", html)


def upsert_place(root: Path, place: dict) -> None:
    if place.get("id") not in PLACE_IDS:
        raise ContentError("Diese Seite gibt es nicht.")
    site = load_site(root)
    places = list(site.get("places") or [])
    for index, item in enumerate(places):
        if item.get("id") == place["id"]:
            places[index] = place
            break
    else:
        raise ContentError("Diese Seite gibt es nicht.")
    site["places"] = places
    save_site(root, site)
    write_place_page(root, place)
    works_path = root / "data" / "works.json"
    works = load_json(works_path) if works_path.is_file() else []
    rebuild_sitemap(root, works)
    rebuild_llms(root, works, site)


def sync_place_images(root: Path, place: dict) -> None:
    folder = place_folder(root, place["id"])
    folder.mkdir(parents=True, exist_ok=True)
    place["images"] = normalize_image_names(folder, place["id"], list(place.get("images") or []))
    prune_extra_images(folder, place["images"])


def add_place_jpeg(root: Path, place: dict, jpeg: bytes) -> None:
    if len(place.get("images") or []) >= MAX_IMAGES:
        raise ContentError("Höchstens 12 Bilder pro Seite.")
    folder = place_folder(root, place["id"])
    folder.mkdir(parents=True, exist_ok=True)
    name = f"upload-{secrets.token_hex(4)}.jpg"
    write_bytes(folder / name, jpeg)
    place.setdefault("images", []).append(name)
    sync_place_images(root, place)
    upsert_place(root, place)


def remove_place_image(root: Path, place: dict, name: str) -> None:
    safe_image_name(name)
    images = list(place.get("images") or [])
    if name not in images:
        raise ContentError("Das Bild gehört nicht zu dieser Seite.")
    if len(images) <= 1:
        raise ContentError("Das letzte Bild bleibt, weil die Startseite es zeigt.")
    images.remove(name)
    place["images"] = images
    path = place_folder(root, place["id"]) / name
    if path.is_file():
        path.unlink()
    sync_place_images(root, place)
    upsert_place(root, place)


def reorder_place_images(root: Path, place: dict, names: list[str]) -> None:
    current = list(place.get("images") or [])
    if sorted(names) != sorted(current) or len(names) != len(current):
        raise ContentError("Die Bilderliste ist unvollständig.")
    for name in names:
        safe_image_name(name)
    place["images"] = names
    sync_place_images(root, place)
    upsert_place(root, place)


def _place_urls(root: Path) -> list[str]:
    path = root / "data" / "site.json"
    if not path.is_file():
        return []
    urls = []
    for place in load_json(path).get("places") or []:
        place_id = place.get("id") or ""
        if place_id in PLACE_IDS:
            urls.append(f"https://wtho.art/images/{place_id}/")
    return urls


def rebuild_sitemap(root: Path, works: list) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    urls = ["https://wtho.art/"] + [f"https://wtho.art/works/{work['id']}/" for work in works] + _place_urls(root)
    for index, loc in enumerate(urls):
        if index == 0:
            freq, priority = "weekly", "1.0"
        elif "/images/" in loc:
            freq, priority = "monthly", "0.6"
        else:
            freq, priority = "monthly", "0.8"
        lines.append("  <url>")
        lines.append(f"    <loc>{loc}</loc>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    write_text(root / "sitemap.xml", "\n".join(lines) + "\n")


_PLACE_LINE = re.compile(r"(?m)^- \[.*?\]\(https://wtho\.art/images/[a-z0-9-]+/\):.*\n?")


def _place_llms_lines(site: dict | None) -> str:
    if not site:
        return ""
    lines = []
    for place in site.get("places") or []:
        place_id = place.get("id") or ""
        if place_id not in PLACE_IDS:
            continue
        title = (place.get("title") or {}).get("en") or (place.get("title") or {}).get("de") or place_id
        text = " ".join(((place.get("text") or {}).get("en") or "").split())
        lines.append(f"- [{title}](https://wtho.art/images/{place_id}/): {text}")
    return "\n".join(lines)


def rebuild_llms(root: Path, works: list, site: dict | None = None) -> None:
    path = root / "llms.txt"
    text = path.read_text(encoding="utf-8") if path.is_file() else "# wtho.art — Thorsten Weitz\n"
    if site:
        email = (site.get("contactEmail") or "").strip()
        instagram = (site.get("instagram") or "").strip()
        if email:
            text = re.sub(r"(?m)^Email:.*$", f"Email: {email}", text, count=1)
        if instagram:
            text = re.sub(r"(?m)^Instagram:.*$", f"Instagram: {instagram}", text, count=1)
    text = _PLACE_LINE.sub("", text)
    marker = "\n## Works\n"
    head = text.split(marker, 1)[0].rstrip() if marker in text else text.rstrip()
    place_lines = _place_llms_lines(site)
    if place_lines:
        head = head + "\n" + place_lines
    lines = [head, "", "## Works"]
    for work in works:
        title = work["title"].get("en") or work["title"].get("de") or work["id"]
        medium = (work.get("medium") or {}).get("en") or ""
        size = work.get("size") or ""
        if size == "—":
            size = ""
        year = work.get("year") or ""
        detail = ", ".join(bit for bit in (medium, size, year) if bit)
        lines.append(f"- [{title}](https://wtho.art/works/{work['id']}/): {detail}")
    write_text(path, "\n".join(lines) + "\n")


def copy_groups(site: dict) -> list[dict]:
    german = site["copy"]["de"]
    english = site["copy"]["en"]
    used: set[str] = set()
    groups = []
    for title, keys in COPY_GROUPS:
        fields = []
        for key, label, long in keys:
            if key not in german and key not in english:
                continue
            fields.append(
                {
                    "key": key,
                    "label": label,
                    "long": long,
                    "de": german.get(key, ""),
                    "en": english.get(key, ""),
                }
            )
            used.add(key)
        if fields:
            groups.append({"title": title, "fields": fields})
    extra = []
    for key in list(german) + [key for key in english if key not in german]:
        if key in used:
            continue
        used.add(key)
        extra.append(
            {
                "key": key,
                "label": key,
                "long": True,
                "de": german.get(key, ""),
                "en": english.get(key, ""),
            }
        )
    if extra:
        groups.append({"title": "Weitere Texte", "fields": extra})
    return groups


def apply_copy(site: dict, form) -> None:
    german = site["copy"]["de"]
    english = site["copy"]["en"]
    keys = list(dict.fromkeys([*german.keys(), *english.keys()]))
    for key in keys:
        de_name = f"de__{key}"
        en_name = f"en__{key}"
        if de_name in form:
            german[key] = form.get(de_name, "").strip()
        if en_name in form:
            english[key] = form.get(en_name, "").strip()
    email = form.get("contactEmail", "").strip()
    instagram = form.get("instagram", "").strip()
    if "@" not in email or " " in email:
        raise ContentError("Die Kontakt-Adresse braucht ein @.")
    if not instagram.startswith("https://"):
        raise ContentError("Instagram muss mit https:// beginnen.")
    site["contactEmail"] = email
    site["instagram"] = instagram


def _rows(form, prefix: str) -> list[dict]:
    years = form.getlist(f"{prefix}_year")
    german = form.getlist(f"{prefix}_de")
    english = form.getlist(f"{prefix}_en")
    rows = []
    for index, (year, de_text, en_text) in enumerate(zip(years, german, english)):
        if form.get(f"{prefix}_drop_{index}"):
            continue
        year, de_text, en_text = year.strip(), de_text.strip(), en_text.strip()
        if not year and not de_text and not en_text:
            continue
        if not year:
            label = "Ausstellung" if prefix == "ex" else "Werdegang"
            raise ContentError(f"Jede {label}-Zeile braucht ein Jahr.")
        rows.append({"year": year, "de": de_text, "en": en_text})
    return rows


def apply_lists(site: dict, form) -> None:
    site["exhibits"] = _rows(form, "ex")
    site["path"] = _rows(form, "path")
