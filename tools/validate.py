#!/usr/bin/env python3
"""Validate generated HTML references, fragments, sitemaps and required outputs."""

from html.parser import HTMLParser
from pathlib import Path
import stat
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET
import json

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = json.loads((ROOT / "content" / "site.json").read_text(encoding="utf-8"))[
    "url"
].rstrip("/")
SKIP = {".git", ".venv", "venv", "__pycache__", "dist", "templates"}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.ids, self.duplicate_ids, self.jsonld, self.social = (
            [],
            set(),
            set(),
            [],
            [],
        )
        self._jsonld = False
        self._jsonld_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        value = attrs.get("id")
        if value:
            if value in self.ids:
                self.duplicate_ids.add(value)
            self.ids.add(value)
        self.refs.extend(value for key in ("href", "src") if (value := attrs.get(key)))
        if (
            tag == "meta"
            and (
                attrs.get("property") in ("og:image",)
                or attrs.get("name") == "twitter:image"
            )
            and attrs.get("content")
        ):
            self.social.append(attrs["content"])
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self._jsonld = True
            self._jsonld_text = []

    def handle_data(self, data):
        if self._jsonld:
            self._jsonld_text.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._jsonld:
            self.jsonld.append("".join(self._jsonld_text))
            self._jsonld = False


errors, pages, id_cache = [], [], {}
for page in ROOT.rglob("*.html"):
    if any(part in SKIP for part in page.relative_to(ROOT).parts):
        continue
    pages.append(page)

for page in pages:
    if not page.stat().st_mode & stat.S_IROTH:
        errors.append(
            f"{page.relative_to(ROOT)}: generated HTML is not world-readable."
        )
    for parent in page.parents:
        if parent == ROOT.parent:
            break
        if not parent.stat().st_mode & stat.S_IXOTH:
            errors.append(
                f"{parent.relative_to(ROOT) if parent != ROOT else '.'}: directory is not world-traversable."
            )
    parser = Links()
    try:
        parser.feed(page.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"{page.relative_to(ROOT)}: cannot read HTML: {exc}")
        continue
    id_cache[page.resolve()] = parser.ids
    for duplicate in parser.duplicate_ids:
        errors.append(f"{page.relative_to(ROOT)}: duplicate id #{duplicate}.")
    for block in parser.jsonld:
        try:
            json.loads(block)
        except json.JSONDecodeError as exc:
            errors.append(f"{page.relative_to(ROOT)}: invalid JSON-LD block: {exc}")
    for image_url in parser.social:
        if not image_url.startswith(SITE_URL + "/"):
            errors.append(
                f"{page.relative_to(ROOT)}: social image is not on the site URL: {image_url}"
            )
        elif not (ROOT / unquote(urlsplit(image_url).path.lstrip("/"))).is_file():
            errors.append(
                f"{page.relative_to(ROOT)}: social image does not exist: {image_url}"
            )
    for ref in parser.refs:
        url = urlsplit(ref)
        if (
            url.scheme
            or url.netloc
            or ref.startswith(("data:", "javascript:", "mailto:", "tel:"))
        ):
            continue
        if url.path.startswith("/"):
            target = (ROOT / unquote(url.path).lstrip("/")).resolve()
        else:
            target = (
                (page.parent / unquote(url.path)).resolve()
                if url.path
                else page.resolve()
            )
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{page.relative_to(ROOT)}: path escapes project: {ref}")
            continue
        if not target.exists():
            errors.append(f"{page.relative_to(ROOT)}: missing {ref}")
            continue
        if url.fragment and target.suffix.lower() == ".html":
            if target not in id_cache:
                try:
                    check = Links()
                    check.feed(target.read_text(encoding="utf-8"))
                    id_cache[target] = check.ids
                except (OSError, UnicodeDecodeError):
                    id_cache[target] = set()
            if unquote(url.fragment) not in id_cache[target]:
                errors.append(
                    f"{page.relative_to(ROOT)}: missing fragment #{url.fragment} in {target.relative_to(ROOT)}"
                )

required = [
    "index.html",
    "404.html",
    "sitemap.xml",
    "sitemap-images.xml",
    "files/cv.pdf",
    "files/statement.pdf",
    "files/press-kit.pdf",
]
for name in required:
    path = ROOT / name
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(f"Missing or empty required output: {name}")
    elif not path.stat().st_mode & stat.S_IROTH:
        errors.append(f"Required output is not world-readable: {name}")
for name in ("sitemap.xml", "sitemap-images.xml"):
    try:
        ET.parse(ROOT / name)
    except (OSError, ET.ParseError) as exc:
        errors.append(f"Invalid {name}: {exc}")

if errors:
    print("VALIDATION FAILED")
    for error in errors:
        print(" - " + error)
    raise SystemExit(1)
print(
    f"VALIDATION PASSED — {len(pages)} HTML files scanned; local assets, links, fragments and XML sitemaps are valid."
)
