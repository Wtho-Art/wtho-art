import json
import shutil
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
    assert "white-space: pre-wrap" in html


def test_render_keeps_statement_line_breaks():
    donor = (REPO / "studio" / "fallback_work.html").read_text(encoding="utf-8")
    donor = donor.replace(" white-space: pre-wrap;", "")
    works = json.loads((REPO / "data" / "works.json").read_text(encoding="utf-8"))
    work = json.loads(json.dumps(next(item for item in works if item["id"] == "touched")))
    work["statement"]["de"] = "Erste Zeile.\r\n\r\nZweite Zeile."
    html = content.render_work_html(donor, work)
    assert ".statement { margin-top: 1.5rem; font-size: 1.0625rem; white-space: pre-wrap; }" in html
    assert "Erste Zeile.\r\n\r\nZweite Zeile." in html


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


def test_format_inline_bold_and_escape():
    assert content._format_inline("**Hallo**") == "<strong>Hallo</strong>"
    assert content._format_inline("A <b> & **B**") == "A &lt;b&gt; &amp; <strong>B</strong>"
    assert content._strip_inline("**Hallo** Welt") == "Hallo Welt"


def test_render_place_statement_bold():
    place = {
        "id": "portrait",
        "title": {"de": "Porträt", "en": "Portrait"},
        "text": {"de": "**Besuch:**\r\n\r\nHallo <tag>", "en": "A line."},
        "images": ["portrait.jpg"],
    }
    html = content.render_place_html(content.FALLBACK_PLACE.read_text(encoding="utf-8"), place)
    statement = html.split('id="statement"', 1)[1].split("</p>", 1)[0]
    assert "<strong>Besuch:</strong>" in statement
    assert "Hallo &lt;tag&gt;" in statement
    assert "**" not in statement
    meta = html.split('name="description"', 1)[1].split(">", 1)[0]
    assert "**" not in meta
    assert "Besuch:" in meta
    assert ".statement strong { font-weight: 600; }" in html
    again = content.render_place_html(html, place)
    assert again == html


def test_render_place_keeps_visit_button():
    donor = content.FALLBACK_PLACE.read_text(encoding="utf-8")
    donor = donor.replace(
        '<p class="statement" id="statement">Porträt im Atelier Freiburg.</p>',
        '<p class="statement" id="statement">Porträt im Atelier Freiburg.</p>\n'
        '        <a class="btn" id="inquireVisit" href="/old">Alt</a>',
        1,
    )
    place = {
        "id": "atelier",
        "title": {"de": "Atelier", "en": "Studio"},
        "text": {"de": "Ein Satz.", "en": "A line."},
        "images": ["atelier.jpg"],
    }
    html = content.render_place_html(donor, place)
    assert 'id="inquireVisit"' in html
    assert 'href="/?visit=atelier#kontakt"' in html
    assert ">Termin anfragen</a>" in html
    assert ".btn {" in html
    again = content.render_place_html(html, place)
    assert again == html


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


def _commissions_root(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    site = {
        "contactEmail": "a@b.c",
        "instagram": "https://instagram.com/x",
        "copy": {"de": {}, "en": {}},
        "places": [],
        "commissions": {
            "title": {"de": "Aufträge & Residenzen", "en": "Commissions & Residencies"},
            "cities": [
                {
                    "id": "london",
                    "title": {"de": "London", "en": "London"},
                    "text": {
                        "de": "**Aufträge** stehen links.\nZweite Zeile.",
                        "en": "Pictures on the left.",
                    },
                    "images": ["london.jpg", "london-2.jpg"],
                }
            ],
        },
    }
    (data / "site.json").write_text(content.dumps_json(site), encoding="utf-8")
    (data / "works.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "llms.txt").write_text("# wtho\n\n## Site\n- [Homepage](https://wtho.art/)\n\n## Works\n", encoding="utf-8")
    folder = tmp_path / "images" / "commissions" / "london"
    folder.mkdir(parents=True)
    return site, folder


def test_render_commissions_page_bold_and_image():
    page = {
        "title": {"de": "Aufträge & Residenzen", "en": "Commissions & Residencies"},
        "cities": [
            {
                "id": "london",
                "title": {"de": "London", "en": "London"},
                "text": {"de": "**Aufträge** & mehr", "en": "A line."},
                "images": ["london.jpg", "london-2.jpg"],
            }
        ],
    }
    html = content.render_commissions_html(content.FALLBACK_COMMISSIONS.read_text(encoding="utf-8"), page)
    assert "<h2>London</h2>" in html
    assert 'src="london/london.jpg"' in html
    assert "<strong>Aufträge</strong>" in html
    assert "&amp; mehr" in html
    assert "https://wtho.art/images/commissions/" in html
    assert "https://wtho.art/images/commissions/london/london.jpg" in html
    again = content.render_commissions_html(html, page)
    assert again == html


def test_city_add_edit_reorder_and_delete(tmp_path):
    _site, folder = _commissions_root(tmp_path)
    (folder / "london.jpg").write_bytes(b"cover")
    (folder / "london-2.jpg").write_bytes(b"second")
    content.write_commissions_page(tmp_path, content.load_site(tmp_path))

    paris = content.add_city(
        tmp_path,
        {
            "title_de": "Paris",
            "title_en": "Paris",
            "text_de": "Ein Satz.",
            "text_en": "A line.",
        },
    )
    assert paris["id"] == "paris"
    page = (tmp_path / "images" / "commissions" / "index.html").read_text(encoding="utf-8")
    assert "<h2>Paris</h2>" in page
    assert 'class="city city-text" id="paris"' in page

    city = content.find_city(content.load_site(tmp_path), "london")
    content.apply_city_fields(city, {"title_de": "London", "title_en": "London", "text_de": "Neu.", "text_en": "New."})
    content.upsert_city(tmp_path, city)
    saved = content.load_site(tmp_path)
    assert content.find_city(saved, "london")["text"]["de"] == "Neu."

    content.reorder_city_images(tmp_path, content.find_city(saved, "london"), ["london-2.jpg", "london.jpg"])
    renamed = content.load_site(tmp_path)
    assert content.find_city(renamed, "london")["images"] == ["london.jpg", "london-2.jpg"]
    assert (folder / "london.jpg").read_bytes() == b"second"

    content.remove_city_image(tmp_path, content.find_city(content.load_site(tmp_path), "london"), "london.jpg")
    content.remove_city_image(tmp_path, content.find_city(content.load_site(tmp_path), "london"), "london.jpg")
    emptied = content.find_city(content.load_site(tmp_path), "london")
    assert emptied["images"] == []
    bare = (tmp_path / "images" / "commissions" / "index.html").read_text(encoding="utf-8")
    assert 'class="city city-text" id="london"' in bare

    content.reorder_cities(tmp_path, ["paris", "london"])
    ordered = [city["id"] for city in content.load_site(tmp_path)["commissions"]["cities"]]
    assert ordered == ["paris", "london"]

    content.delete_city(tmp_path, "paris")
    left = content.load_site(tmp_path)
    assert [city["id"] for city in left["commissions"]["cities"]] == ["london"]
    assert not (tmp_path / "images" / "commissions" / "paris").exists()
    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert "https://wtho.art/images/commissions/" in sitemap
    assert "[Commissions &amp; Residencies]" not in llms
    assert "[Commissions & Residencies](https://wtho.art/images/commissions/):" in llms
    assert "London: New." in llms
    assert "## Works" in llms


def test_homepage_seo_patches_tags_and_identity(tmp_path):
    shutil.copy(REPO / "index.html", tmp_path / "index.html")
    data = tmp_path / "data"
    data.mkdir()
    site = {
        "contactEmail": "a@b.c",
        "instagram": "https://instagram.com/x",
        "copy": {"de": {}, "en": {}},
        "seo": {
            "title": "Neuer Titel",
            "description": "Neue Beschreibung",
            "keywords": "alpha, beta",
            "author": "Thorsten Weitz",
            "robots": "index, follow",
            "ogTitle": "OG Titel",
            "ogDescription": "OG Text",
            "jobTitle": "Maler",
            "personDescription": "Kurztext",
            "addressLocality": "Basel",
        },
    }
    (data / "site.json").write_text(content.dumps_json(site), encoding="utf-8")
    (data / "works.json").write_text("[]\n", encoding="utf-8")
    content.apply_seo(site, site["seo"])
    content.write_homepage_seo(tmp_path, site)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "<title>Neuer Titel</title>" in html
    assert 'name="description" content="Neue Beschreibung"' in html
    assert 'name="keywords" content="alpha, beta"' in html
    assert 'property="og:title" content="OG Titel"' in html
    assert 'property="og:description" content="OG Text"' in html
    assert 'name="twitter:title" content="OG Titel"' in html
    assert 'name="twitter:description" content="OG Text"' in html
    assert '"jobTitle": "Maler"' in html
    assert '"addressLocality": "Basel"' in html
    assert '"description": "Kurztext"' in html
    assert "mailto:a@b.c" in html

    site["contactEmail"] = "neu@b.c"
    site["instagram"] = "https://instagram.com/neu"
    content.save_site(tmp_path, site)
    (tmp_path / "llms.txt").write_text(
        "# Heading\n\n> Summary stays\n\nPreferred name: N\nStudio: S\nEmail: a@b.c\n"
        "Instagram: https://instagram.com/x\n\n## Site\n- [Homepage](https://wtho.art/): Home\n\n## Works\n",
        encoding="utf-8",
    )
    content.rebuild_llms(tmp_path, [], site)
    content.sync_homepage_identity(tmp_path, site)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert "mailto:neu@b.c" in html
    assert "https://instagram.com/neu" in html
    assert "<title>Neuer Titel</title>" in html
    assert "Email: neu@b.c" in llms
    assert "Instagram: https://instagram.com/neu" in llms
    assert "> Summary stays" in llms


def test_robots_keeps_sitemap_and_rejects_junk(tmp_path):
    saved = content.save_robots(tmp_path, "User-agent: *\nAllow: /\nSitemap: https://evil.example/\n")
    assert saved.endswith("Sitemap: https://wtho.art/sitemap.xml\n")
    assert "evil" not in saved
    assert (tmp_path / "robots.txt").read_text(encoding="utf-8") == saved
    for bad in ("<script>", "x" * 5001, "a\x00b"):
        try:
            content.save_robots(tmp_path, bad)
        except content.ContentError:
            continue
        raise AssertionError(bad[:12])


def test_llms_summary_survives_rebuild(tmp_path):
    text = "\n".join(
        [
            "# Old heading",
            "",
            "> Old summary",
            "",
            "Preferred name: A",
            "Studio: B",
            "Email: a@b.c",
            "Instagram: https://instagram.com/x",
            "",
            "## Site",
            "- [Homepage](https://wtho.art/): Home line",
            "- [Instagram](https://instagram.com/x): IG line",
            "- [Portrait](https://wtho.art/images/portrait/): old place",
            "",
            "## Works",
            "- [Blue](https://wtho.art/works/blue/): hand note",
            "",
        ]
    )
    site = {
        "contactEmail": "a@b.c",
        "instagram": "https://instagram.com/x",
        "places": [],
        "copy": {"de": {}, "en": {}},
    }
    fields = {
        "heading": "New heading",
        "summary": "New summary",
        "preferredName": "Thorsten Weitz",
        "studio": "Freiburg",
        "homepage": "Artist and studio",
        "instagramBlurb": "Process",
    }
    updated = content.apply_llms_fields(text, fields, site)
    assert "> New summary" in updated
    assert "- [Homepage](https://wtho.art/): Artist and studio" in updated
    assert "- [Instagram](https://instagram.com/x): Process" in updated
    assert "- [Blue](https://wtho.art/works/blue/): hand note" in updated
    try:
        content.apply_llms_fields(text, {**fields, "summary": "bad ## Works"}, site)
    except content.ContentError:
        pass
    else:
        raise AssertionError("works marker was accepted")

    data = tmp_path / "data"
    data.mkdir()
    (data / "site.json").write_text(content.dumps_json(site), encoding="utf-8")
    (data / "works.json").write_text(
        content.dumps_json(
            [
                {
                    "id": "blue",
                    "title": {"en": "Blue", "de": "Blau"},
                    "medium": {"en": "Oil", "de": "Öl"},
                    "size": "10 cm",
                    "year": "2026",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "llms.txt").write_text(updated, encoding="utf-8")
    content.rebuild_llms(tmp_path, content.load_works(tmp_path), site)
    llms = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert "> New summary" in llms
    assert "[Blue](https://wtho.art/works/blue/): Oil, 10 cm, 2026" in llms
    assert "hand note" not in llms
