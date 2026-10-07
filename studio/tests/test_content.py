import json
from pathlib import Path

import content

REPO = Path(__file__).resolve().parents[2]


def test_slug_and_unique_id():
    assert content.slugify("The dance of duality") == "the-dance-of-duality"
    assert content.slugify("Größe für Öl") == "grosse-fur-ol"
    assert content.slugify("...") == "werk"
    works = [{"id": "werk"}, {"id": "werk-2"}]
    assert content.unique_id(works, "werk") == "werk-3"


def test_real_json_round_trip():
    for name in ("works.json", "site.json"):
        raw = (REPO / "data" / name).read_text(encoding="utf-8")
        assert content.dumps_json(json.loads(raw)) == raw


def test_every_copy_key_is_editable():
    site = json.loads((REPO / "data" / "site.json").read_text(encoding="utf-8"))
    grouped = {field["key"] for group in content.copy_groups(site) for field in group["fields"]}
    assert set(site["copy"]["de"]) <= grouped
    assert set(site["copy"]["en"]) <= grouped


def test_render_real_work_page_keeps_design():
    donor = (REPO / "works" / "touched" / "index.html").read_text(encoding="utf-8")
    works = json.loads((REPO / "data" / "works.json").read_text(encoding="utf-8"))
    work = json.loads(json.dumps(next(item for item in works if item["id"] == "touched")))
    work["statement"]["de"] = 'Neu & "Zitat" <b>'
    work["title"]["de"] = "Neuer Titel"
    html = content.render_work_html(donor, work)
    assert "Neu &amp; &quot;Zitat&quot; &lt;b&gt;" in html
    assert "Violett und Blau in einem Sog der Berührung." not in html
    assert "<title>Neuer Titel — wtho.art</title>" in html
    assert "https://wtho.art/works/touched/touched.jpg" in html
    assert "--rupture: #b54432" in html
    assert "\\u003c" not in html or "<b>" not in html.split("application/ld+json", 1)[1].split("</script>", 1)[0]
    assert '"name": "Neuer Titel"' in html


def test_rejects_path_escape():
    try:
        content.work_folder(REPO, "../data")
    except content.ContentError:
        return
    raise AssertionError("path escape was accepted")


def test_image_normalize_and_prune(tmp_path):
    folder = tmp_path / "works" / "blue"
    folder.mkdir(parents=True)
    (folder / "b.jpg").write_bytes(b"second")
    (folder / "a.jpg").write_bytes(b"first")
    (folder / "notes.txt").write_bytes(b"keep-me")
    (folder / "stray.png").write_bytes(b"png")
    names = content.normalize_image_names(folder, "blue", ["b.jpg", "a.jpg"])
    assert names == ["blue.jpg", "blue-2.jpg"]
    assert (folder / "blue.jpg").read_bytes() == b"second"
    assert (folder / "blue-2.jpg").read_bytes() == b"first"
    content.prune_extra_images(folder, names)
    assert (folder / "notes.txt").read_bytes() == b"keep-me"
    assert not (folder / "stray.png").exists()


def test_sitemap_and_llms(tmp_path):
    (tmp_path / "llms.txt").write_text(
        "# wtho.art\n\nEmail: old@example.com\nInstagram: https://example.invalid\n\n## Works\n- old\n",
        encoding="utf-8",
    )
    works = [
        {
            "id": "blue",
            "year": "2026",
            "size": "10 × 20 cm",
            "title": {"de": "Blau", "en": "Blue"},
            "medium": {"de": "Öl", "en": "Oil"},
            "statement": {"de": "", "en": ""},
            "images": ["blue.jpg"],
        }
    ]
    site = {"contactEmail": "Wtho.Art@proton.me", "instagram": "https://www.instagram.com/wtho.art"}
    content.rebuild_sitemap(tmp_path, works)
    content.rebuild_llms(tmp_path, works, site)
    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert "https://wtho.art/works/blue/" in sitemap
    assert "datenschutz" not in sitemap
    assert "Email: Wtho.Art@proton.me" in llms
    assert "[Blue](https://wtho.art/works/blue/): Oil, 10 × 20 cm, 2026" in llms
    assert "- old" not in llms


def test_upsert_writes_page_from_fallback(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "works.json").write_text("[]\n", encoding="utf-8")
    (data / "site.json").write_text(
        json.dumps({"contactEmail": "a@b.c", "instagram": "https://instagram.com/x", "copy": {"de": {}, "en": {}}}),
        encoding="utf-8",
    )
    (tmp_path / "llms.txt").write_text("# wtho\n\n## Works\n", encoding="utf-8")
    work = content.blank_work()
    work.update(
        {
            "id": "blue-note",
            "year": "2026",
            "title": {"de": "Blaue Note", "en": "Blue Note"},
            "medium": {"de": "Öl auf Leinwand", "en": "Oil on canvas"},
            "statement": {"de": "Ein Satz.", "en": "A line."},
        }
    )
    content.upsert_work(tmp_path, work)
    page = (tmp_path / "works" / "blue-note" / "index.html").read_text(encoding="utf-8")
    assert "<title>Blaue Note — wtho.art</title>" in page
    assert "https://wtho.art/works/blue-note/" in page
    assert "--rupture" in page
    saved = json.loads((data / "works.json").read_text(encoding="utf-8"))
    assert saved[0]["id"] == "blue-note"


def _place_root(tmp_path, images):
    data = tmp_path / "data"
    data.mkdir()
    place = {
        "id": "portrait",
        "title": {"de": "Porträt", "en": "Portrait"},
        "text": {
            "de": "Porträt im Atelier Freiburg. Dieser Text ist ein Platzhalter.",
            "en": "Portrait in the Freiburg studio. This text is a placeholder.",
        },
        "images": images,
    }
    site = {
        "contactEmail": "a@b.c",
        "instagram": "https://instagram.com/x",
        "copy": {"de": {}, "en": {}},
        "places": [place],
    }
    (data / "site.json").write_text(content.dumps_json(site), encoding="utf-8")
    (data / "works.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("# wtho\n\n## Site\n- [Homepage](https://wtho.art/)\n\n## Works\n", encoding="utf-8")
    folder = tmp_path / "images" / "portrait"
    folder.mkdir(parents=True)
    return place, folder


def test_render_place_page_keeps_slots():
    place = {
        "id": "portrait",
        "title": {"de": "Porträt", "en": "Portrait"},
        "text": {"de": "Ein Satz & mehr.", "en": "A line."},
        "images": ["portrait.jpg", "portrait-2.jpg"],
    }
    html = content.render_place_html(content.FALLBACK_PLACE.read_text(encoding="utf-8"), place)
    assert "<title>Porträt — wtho.art</title>" in html
    assert "https://wtho.art/images/portrait/" in html
    assert 'src="portrait.jpg"' in html
    assert "Ein Satz &amp; mehr." in html
    assert "https://wtho.art/images/portrait/portrait.jpg" in html
    again = content.render_place_html(html, place)
    assert again == html


def test_place_keeps_last_image_and_renames_cover(tmp_path):
    place, folder = _place_root(tmp_path, ["portrait.jpg"])
    (folder / "portrait.jpg").write_bytes(b"cover")
    try:
        content.remove_place_image(tmp_path, place, "portrait.jpg")
    except content.ContentError:
        pass
    else:
        raise AssertionError("last image was removed")
    assert (folder / "portrait.jpg").read_bytes() == b"cover"

    (folder / "portrait-2.jpg").write_bytes(b"second")
    place["images"] = ["portrait.jpg", "portrait-2.jpg"]
    content.reorder_place_images(tmp_path, place, ["portrait-2.jpg", "portrait.jpg"])
    saved = json.loads((tmp_path / "data" / "site.json").read_text(encoding="utf-8"))
    assert saved["places"][0]["images"] == ["portrait.jpg", "portrait-2.jpg"]
    assert (folder / "portrait.jpg").read_bytes() == b"second"
    assert (folder / "portrait-2.jpg").read_bytes() == b"cover"
    page = (folder / "index.html").read_text(encoding="utf-8")
    assert 'src="portrait.jpg"' in page
    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert "https://wtho.art/images/portrait/" in sitemap
    assert "https://wtho.art/images/atelier/" not in sitemap
    assert "[Portrait](https://wtho.art/images/portrait/):" in llms
    assert "## Works" in llms
