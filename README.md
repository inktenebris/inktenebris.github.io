# INKTENEBRIS — Artist Website & Local CMS

A lightweight, fully data-driven static artist website. Central content files generate every public HTML page, artwork detail page, navigation, SEO metadata, XML sitemap and downloadable PDF. The private CMS runs locally on your computer; the published website remains static and fast.

## Requirements

- Python 3.10 or newer
- Free Python packages listed in `requirements.txt`
- Git for version control

## First-time setup (Linux Mint)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Open the local CMS

```bash
source .venv/bin/activate
./start-cms.sh
```

Open **http://127.0.0.1:8765** in your browser. The dashboard only listens on your own computer; it is not deployed publicly. Use the Artist & Contact form for common profile changes, the Add Artwork form to create an artwork record and add it to the gallery, or the advanced JSON editor for every other page, section, navigation item and setting. Save your changes, then build the website.

## Build and validate everything

```bash
source .venv/bin/activate
./build-site.sh
```

This generates the complete website and all three PDFs, checks required content and image references, then checks local HTML links. The generated site files are written to the repository root to remain compatible with the existing GitHub Pages layout.

To create the clean deployment folder used by GitHub Actions:

```bash
python tools/package_site.py
```

To preview the packaged website locally, run this in a second terminal:

```bash
python -m http.server 8000 --bind 127.0.0.1 --directory dist
```

Open **http://127.0.0.1:8000**. The preview server stays on your computer and does not expose the CMS or source content.

## Where to edit content

| File                      | Controls                                                                             |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `content/site.json`       | Site name, URL, contact email, social links, logo, SEO, newsletter, copyright        |
| `content/artist.json`     | Artist identity, biography, artist statement, CV profile, skills and software        |
| `content/navigation.json` | All primary, information and footer links                                            |
| `content/homepage.json`   | Hero, intro, featured showcases, selected gallery, manifesto, contact and newsletter |
| `content/artworks.json`   | Artwork title, slug, image, date, dimensions, description and quote                  |
| `content/pages.json`      | Artist statement, CV, exhibitions, press, press kit, privacy and terms page sections |
| `content/documents.json`  | PDF document titles                                                                  |
| `content/error.json`      | 404 page text                                                                        |

## Add an artwork

1. Put the image in `images/artworks/`.
2. Add one artwork record to `content/artworks.json`. Copy an existing record as a starting point and give it a unique slug.
3. Add the new slug to `content/homepage.json` → `selected.artworks` if it should appear in the homepage gallery.
4. Run `./build-site.sh`.

The detail page, gallery card, navigation order, CV selected works, press-kit selected works, PDF documents and image sitemap are generated from that record. Artwork order in `artworks.json` controls the gallery and previous/next navigation.

## Edit a page

Edit its section data in `content/pages.json`. All page layouts use shared templates in `templates/`. Do not edit generated `index.html`, `pages/*.html`, `legal/*.html` or `artworks/*.html` directly; the next build regenerates them.

## Deployment

A GitHub Actions workflow is included at `.github/workflows/pages.yml`. It installs the free dependencies, builds and validates the site, packages only public website files into `dist/`, and deploys to GitHub Pages.

In GitHub, open **Settings → Pages → Build and deployment → Source** and select **GitHub Actions**. Then commit and push to the `main` branch. The workflow deploys the generated static site. GitHub Pages is free for public repositories under the applicable GitHub Free plan limits.

## Important architecture notes

- No runtime database or paid CMS service is required.
- No API key is required.
- The published site is static HTML/CSS/JS; Python is only needed locally and in the build workflow.
- The admin dashboard is local-only. Do not expose it to the public internet.
- The existing visual stylesheet, artwork assets, animations and page URLs are retained.
- GSAP 3.12.5 is self-hosted in `assets/vendor/` (no CDN). Google Fonts remain an optional external resource; the site falls back to system fonts without it.
- PDFs use Helvetica. If you add characters it cannot draw (e.g. Bengali), the build prints a warning.
- `qr_code/qr.py` is a local-only helper (not published). Install its dependency with `python -m pip install -r requirements-dev.txt`.
- The sitemap only lists `lastmod` for artworks (their own date).
