#!/usr/bin/env python3
"""Local-only INKTENEBRIS CMS. It binds to 127.0.0.1, never to the network."""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit
from pathlib import Path
import json, os, subprocess, sys, html, re, tempfile
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.build import image_dimensions, safe_file

CONTENT = ROOT / "content"
ALLOWED = {
    "site.json",
    "artist.json",
    "navigation.json",
    "homepage.json",
    "pages.json",
    "artworks.json",
    "documents.json",
    "error.json",
}

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>INKTENEBRIS CMS</title><style>
*{box-sizing:border-box}body{margin:0;background:#090909;color:#eee;font:14px/1.55 system-ui,sans-serif}header{padding:24px 5vw;border-bottom:1px solid #292929;display:flex;justify-content:space-between;align-items:center}header strong{letter-spacing:.18em}main{max-width:1180px;margin:36px auto;padding:0 22px}.eyebrow{color:#aaa;letter-spacing:.16em;font-size:11px}.grid{display:grid;grid-template-columns:220px 1fr;gap:20px}.panel{background:#111;border:1px solid #292929;border-radius:12px;padding:18px;margin-bottom:18px}.files a{display:block;color:#bbb;text-decoration:none;padding:9px;border-radius:7px}.files a.active,.files a:hover{background:#242424;color:#fff}.editor textarea{width:100%;min-height:54vh;background:#080808;color:#d8d8d8;border:1px solid #333;border-radius:8px;padding:16px;font:13px/1.6 ui-monospace,monospace;resize:vertical}.buttons{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}button,.button{background:#eee;color:#111;border:0;border-radius:7px;padding:11px 16px;font-weight:700;cursor:pointer;text-decoration:none}button.secondary{background:#242424;color:#eee;border:1px solid #444}.note{color:#999;font-size:12px}.status{padding:12px;border:1px solid #393939;border-radius:8px;margin-bottom:18px}.ok{color:#9ee6ae}.bad{color:#ff9b9b}code{color:#c6a6ff}.quick{display:grid;grid-template-columns:1fr 1fr;gap:18px}.field{display:flex;flex-direction:column;gap:5px;margin:10px 0}.field label{font-size:12px;color:#aaa}.field input,.field textarea{width:100%;background:#080808;color:#eee;border:1px solid #333;border-radius:7px;padding:10px;font:inherit}.field textarea{min-height:100px;resize:vertical}.wide{grid-column:1/-1}.small{font-size:11px;color:#888}@media(max-width:760px){.grid,.quick{grid-template-columns:1fr}.files{display:grid;grid-template-columns:1fr 1fr}.editor textarea{min-height:45vh}}
</style></head><body><header><strong>INKTENEBRIS <span style="color:#aaa">/ CMS</span></strong><span class="eyebrow">LOCAL CONTENT CONTROL</span></header><main><p class="eyebrow">CONTENT MANAGEMENT SYSTEM</p><h1 style="font-size:34px;margin:4px 0 8px">Control the entire website.</h1><p class="note">Edit central content once, then rebuild every HTML page, sitemap and PDF. This dashboard runs only on this computer and is never published.</p>{status}{quickforms}<div class="grid"><aside class="panel files"><h3>All content sources</h3>{links}</aside><section class="panel editor"><form method="post" action="/save"><input type="hidden" name="file" value="{filename}"><label for="content"><b>{filename}</b></label><p class="note">Advanced JSON editor · Use this for page copy, navigation, homepage sections, legal text, settings and other content. Your previous version is backed up as <code>.bak</code>.</p><textarea id="content" name="content" spellcheck="false">{content}</textarea><div class="buttons"><button type="submit">Save content</button></div></form><form method="post" action="/build" class="buttons"><button class="secondary" type="submit">Build entire website + PDFs</button></form><p class="note">The build validates content, generates pages and PDFs, and refreshes both sitemaps.</p></section></div><div class="panel"><h3>How publishing works</h3><ol><li>Edit content in the quick forms or source editor.</li><li>Save your changes.</li><li>Build the entire website.</li><li>Preview locally, then commit and push to GitHub.</li></ol><p class="note">For a new artwork, first copy its image into <code>images/artworks/</code>, then use the artwork form above. The form adds the record and places it in the homepage gallery automatically.</p></div></main></body></html>"""


def reject_json_constant(value):
    raise ValueError(f"Invalid JSON constant: {value}")


def read_json(name):
    return json.loads(
        (CONTENT / name).read_text(encoding="utf-8"),
        parse_constant=reject_json_constant,
    )


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def write_json(name, data):
    atomic_write(
        CONTENT / name,
        json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
    )


def write_json_many(items):
    originals = {name: (CONTENT / name).read_text(encoding="utf-8") for name in items}
    try:
        for name, raw in originals.items():
            atomic_write((CONTENT / name).with_suffix(".json.bak"), raw)
        for name, value in items.items():
            write_json(name, value)
    except Exception:
        for name, raw in originals.items():
            atomic_write(CONTENT / name, raw)
        raise


def field(label, name, value="", kind="input", wide=False):
    cls = "field wide" if wide else "field"
    val = html.escape(str(value or ""), quote=True)
    if kind == "textarea":
        control = f'<textarea name="{name}">{html.escape(str(value or ""))}</textarea>'
    else:
        control = f'<input name="{name}" value="{val}" required>'
    return f'<div class="{cls}"><label>{label}</label>{control}</div>'


def quick_forms():
    artist = read_json("artist.json")
    site = read_json("site.json")
    bio = "\n\n".join(artist.get("biography", []))
    profile = """<div class="quick">
<form class="panel" method="post" action="/save-profile"><h3>Artist & contact profile</h3><p class="note">These fields feed the homepage, About, CV, press kit and contact links.</p>"""
    for label, name, value in [
        ("Artist name", "name", artist.get("name")),
        ("Professional name", "professional_name", artist.get("professional_name")),
        ("Location", "location", artist.get("location")),
        ("Practice", "practice", artist.get("practice")),
        ("Medium", "medium", artist.get("medium")),
        ("Style", "style", artist.get("style")),
        ("Public email", "email", site.get("email")),
    ]:
        profile += field(label, name, value)
    profile += (
        field(
            "Artist statement", "statement", artist.get("statement"), "textarea", True
        )
        + field(
            "Biography paragraphs (separate with a blank line)",
            "biography",
            bio,
            "textarea",
            True,
        )
        + '<button type="submit">Save artist profile</button></form>'
    )
    artwork = """<form class="panel" method="post" action="/add-artwork"><h3>Add artwork</h3><p class="note">Copy the image into <code>images/artworks/</code> first. The new record is added to the gallery and all generated documents.</p>"""
    for label, name, value in [
        ("Title", "title", ""),
        ("Unique slug (e.g. new-drawing)", "slug", ""),
        ("Image path inside images/ (e.g. artworks/art11.jpg)", "image", ""),
        ("Creation date (YYYY-MM-DD)", "date", ""),
        ("Dimensions", "dimensions", "210 × 297 mm (A4)"),
        ("Description", "description", ""),
        ("Quote", "quote", ""),
    ]:
        artwork += field(
            label,
            name,
            value,
            "textarea" if name in ("description", "quote") else "input",
            name in ("description", "quote"),
        )
    artwork += (
        '<button type="submit">Add artwork + update gallery</button></form></div>'
    )
    return profile + artwork


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, body, status=200):
        data = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, path):
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()

    def do_GET(self):
        file = self.path.split("?", 1)[0].lstrip("/") or "site.json"
        if file not in ALLOWED:
            file = "site.json"
        path = CONTENT / file
        content = path.read_text(encoding="utf-8") if path.exists() else "{}"
        links = "".join(
            f'<a class="{"active" if n == file else ""}" href="/{n}">{n}</a>'
            for n in sorted(ALLOWED)
        )
        status = ""
        if "saved" in self.path:
            status = '<div class="status ok">Changes saved. Rebuild the website to regenerate every output.</div>'
        if "added" in self.path:
            status = '<div class="status ok">Artwork added. Its detail page, gallery entry and document references will be generated on the next build.</div>'
        if "built" in self.path:
            status = '<div class="status ok">Build completed successfully. All generated pages, sitemaps and PDFs are updated.</div>'
        if "error" in self.path:
            status = '<div class="status bad">Build failed. Check the terminal for validation details.</div>'
        values = {
            "status": status,
            "quickforms": quick_forms(),
            "links": links,
            "filename": html.escape(file),
            "content": html.escape(content),
        }
        self.send(
            re.sub(
                r"\{(status|quickforms|links|filename|content)\}",
                lambda m: values[m.group(1)],
                PAGE,
            )
        )

    def do_POST(self):
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "").lower()
        if origin not in (
            "http://127.0.0.1:8765",
            "http://localhost:8765",
        ) or host not in ("127.0.0.1:8765", "localhost:8765"):
            return self.send("Same-origin request required", 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.send("Invalid request length", 400)
        if length < 0:
            return self.send("Invalid request length", 400)
        if length > 2_000_000:
            return self.send("Request too large", 413)
        try:
            data = parse_qs(
                self.rfile.read(length).decode("utf-8"), max_num_fields=1000
            )
        except (UnicodeDecodeError, ValueError):
            return self.send("Invalid form data", 400)
        route = urlsplit(self.path).path
        if route == "/save":
            file = data.get("file", [""])[0]
            raw = data.get("content", [""])[0]
            if file not in ALLOWED:
                return self.send("Invalid content file", 400)
            try:
                parsed = json.loads(raw, parse_constant=reject_json_constant)
            except ValueError as e:
                return self.send(
                    f'<p>Invalid JSON: {html.escape(str(e))}</p><a href="/{html.escape(file)}">Go back</a>',
                    400,
                )
            expected = list if file == "artworks.json" else dict
            if not isinstance(parsed, expected):
                return self.send(
                    f"{file} must contain a JSON {expected.__name__}.", 400
                )
            target = CONTENT / file
            if target.exists():
                atomic_write(
                    target.with_suffix(".json.bak"), target.read_text(encoding="utf-8")
                )
            write_json(file, parsed)
            return self.redirect(f"/{file}?saved=1")
        if route == "/save-profile":
            artist = read_json("artist.json")
            site = read_json("site.json")
            for key in (
                "name",
                "professional_name",
                "location",
                "practice",
                "medium",
                "style",
                "statement",
            ):
                artist[key] = data.get(key, [""])[0].strip()
            artist["biography"] = [
                x.strip()
                for x in re.split(r"\n\s*\n", data.get("biography", [""])[0])
                if x.strip()
            ]
            site["email"] = data.get("email", [""])[0].strip()
            missing = [
                k
                for k in (
                    "name",
                    "professional_name",
                    "location",
                    "practice",
                    "medium",
                    "style",
                    "statement",
                )
                if not artist[k]
            ]
            if missing:
                return self.send(
                    "These fields are required: " + html.escape(", ".join(missing)), 400
                )
            if not artist["biography"]:
                return self.send("Biography needs at least one paragraph.", 400)
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", site["email"]):
                return self.send("A valid public email is required.", 400)
            write_json_many({"artist.json": artist, "site.json": site})
            return self.redirect("/artist.json?saved=1")
        if route == "/add-artwork":
            artworks = read_json("artworks.json")
            home = read_json("homepage.json")
            selected = home.get("selected")
            if (
                not isinstance(artworks, list)
                or not isinstance(selected, dict)
                or not isinstance(selected.get("artworks"), list)
            ):
                return self.send(
                    "Artwork or homepage content has an invalid structure. Fix the JSON first.",
                    400,
                )
            item = {
                k: data.get(k, [""])[0].strip()
                for k in (
                    "title",
                    "slug",
                    "image",
                    "date",
                    "dimensions",
                    "description",
                    "quote",
                )
            }
            if not all(item.values()):
                return self.send("All artwork fields are required.", 400)
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", item["slug"]):
                return self.send(
                    "Slug must use lowercase letters, numbers and hyphens.", 400
                )
            try:
                date.fromisoformat(item["date"])
            except ValueError:
                return self.send("Date must use YYYY-MM-DD.", 400)
            if any(w.get("slug") == item["slug"] for w in artworks):
                return self.send("That artwork slug already exists.", 400)
            image = safe_file(ROOT / "images", item["image"])
            if image is None:
                return self.send(
                    'Image path must be a plain relative path inside images/ (no "..", no backslashes).',
                    400,
                )
            if (
                image.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp")
                or not image.is_file()
            ):
                return self.send(
                    "Choose an existing JPG, PNG or WebP image inside images/.", 400
                )
            try:
                image_dimensions(image)
            except (OSError, ValueError):
                return self.send("The selected image is corrupt or unsupported.", 400)
            artworks.append(item)
            selected["artworks"].append(item["slug"])
            write_json_many({"artworks.json": artworks, "homepage.json": home})
            return self.redirect("/artworks.json?added=1")
        if route == "/build":
            result = subprocess.run(
                ["bash", str(ROOT / "build-site.sh")],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return self.redirect("/site.json?built=1")
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            return self.redirect("/site.json?error=1")
        self.send("Not found", 404)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8765), Handler)
    print("INKTENEBRIS CMS running at http://127.0.0.1:8765")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCMS stopped.")
