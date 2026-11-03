# INKTENEBRIS content system

All public site content is maintained in this directory. HTML files are generated outputs; edit the JSON sources and rebuild instead of editing generated HTML directly.

## Content sources

- `site.json` — site identity, URL, contact, social links, assets, newsletter and SEO defaults.
- `artist.json` — artist identity, biography, statement, CV profile, skills and software.
- `navigation.json` — primary, information and footer navigation.
- `homepage.json` — homepage hero, intro, showcase, selected works, manifesto, contact and newsletter sections.
- `pages.json` — all informational and legal page copy and section definitions.
- `artworks.json` — artwork records and metadata.
- `documents.json` — document-generation configuration.
- `error.json` — 404 page content.

## Build

```bash
python3 -m pip install -r requirements.txt
python3 tools/build.py
```

The build validates references and artwork assets, then generates all HTML pages, XML sitemaps and the CV, artist statement and press-kit PDFs.

## Local CMS

```bash
python3 admin/dashboard.py
```

Open http://127.0.0.1:8765. The dashboard binds to localhost only. Edit JSON sources, save, and run the build from the dashboard.

## New artwork

1. Add the image to `images/artworks/`.
2. Add a unique record to `artworks.json` (slug, title, image, date, dimensions, description, quote).
3. Add its slug to `homepage.json` under `selected.artworks` if it should appear in the homepage gallery.
4. Run the build. Artwork detail pages, homepage cards, CV/press-kit selections and sitemaps are generated from that record.

## Deployment

The repository root remains the GitHub Pages publishing directory. Commit the generated HTML, PDFs and sitemaps together with the content sources and templates.
