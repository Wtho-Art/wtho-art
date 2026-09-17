# How to change text and pictures

You do **not** need to edit HTML for normal updates.
You do **not** need an admin site.

## Files that matter

| File | What it is |
|---|---|
| `data/works.json` | Every painting: title, size, year, DE/EN text, extra photos |
| `data/site.json` | Hero painting, bio, exhibitions, Werdegang, nav labels |
| `works/<id>/<file>.jpg` | Pictures that actually show on the site |

`id` is the folder name, for example `dance-of-duality`.

## Change a text (Gemini / Grok)

1. Open `data/works.json`.
2. Paste the one work (or the whole file) into the AI.
3. Ask for a DE + EN statement in the same voice. Do not let it invent sizes or years.
4. Put the JSON back. Keep commas and quotes valid.
5. Commit and push.

Site strings (nav, about, newsletter) live under `copy.de` and `copy.en` in `data/site.json`.

## Change the big homepage painting

In `data/site.json`:

```json
"heroWorkId": "dance-of-duality"
```

Use the work `id` (folder name). Caption and image follow automatically.

## Add a painting

1. Create `works/my-new-work/`.
2. Put a web JPEG in it, named `my-new-work.jpg` (long edge about 1600–2400 px).
3. Copy an existing block in `data/works.json`, change the fields, set `"id": "my-new-work"`.
4. Keep originals (TIFF, huge JPEG) **out of this folder**. Store them next to the repo, not inside Git.

## Add extra views of one painting

1. Drop `my-new-work-detail.jpg` into the same folder.
2. In that work’s JSON:

```json
"images": ["my-new-work.jpg", "my-new-work-detail.jpg"]
```

The first file is the cover (homepage + first view). The rest become thumbnails on the work page.

## Publish

On the laptop, in Git Cola or GitHub Desktop:

1. Pull
2. Commit a short message (`Add detail shot for Duality`)
3. Push `main` (SSH key, no token needed once `ssh -T git@github.com` works)

GitHub is the source of truth. Do not edit the site through a hosting control panel.

## Do not

- Put master TIFFs in Git (GitHub limit 100 MB per file; repo gets slow).
- Change `index.html` for a new painting — JSON is enough.
