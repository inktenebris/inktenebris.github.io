#!/usr/bin/env python3
"""Build every INKTENEBRIS page, sitemap and PDF from centralized content."""
from __future__ import annotations
import json, os, re, sys, tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, unquote
from xml.sax.saxutils import escape as xml_escape
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'content'
TEMPLATES = ROOT / 'templates'


def reject_json_constant(value):
    raise ValueError(f'Invalid JSON constant: {value}')


def load_json(name):
    path = CONTENT / name
    try:
        value = json.loads(path.read_text(encoding='utf-8'), parse_constant=reject_json_constant)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read content/{name}: {exc}") from exc
    expected = list if name == 'artworks.json' else dict
    if not isinstance(value, expected):
        raise ValueError(f"content/{name} must contain a JSON {expected.__name__}.")
    return value


def atomic_write(path: Path, value: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def save_text(path: Path, value: str):
    atomic_write(path, value.rstrip() + '\n')


def safe_file(base: Path, relative: str):
    if not isinstance(relative, str) or not relative.strip() or '\\' in relative or '\x00' in relative:
        return None
    candidate = Path(relative)
    if candidate.is_absolute() or '..' in candidate.parts:
        return None
    target = (base / candidate).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        return None
    return target


def valid_web_url(value):
    try:
        parsed = urlsplit(value)
        return bool(parsed.scheme in ('http', 'https') and parsed.hostname
                    and not parsed.username and not parsed.password and parsed.port != 0)
    except (TypeError, ValueError):
        return False


def json_for_html(value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    return Markup(raw.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))


def safe_linebreaks(value):
    raw = str(escape(value))
    return Markup(re.sub(r'&lt;br\s*/?&gt;', '<br />', raw, flags=re.I))


def image_dimensions(path: Path):
    with path.open('rb') as f:
        head = f.read(30)
        if head.startswith(b'\x89PNG\r\n\x1a\n') and head[12:16] == b'IHDR':
            width, height = int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')
        elif head[:4] == b'RIFF' and head[8:12] == b'WEBP':
            kind = head[12:16]
            if kind == b'VP8X':
                width = int.from_bytes(head[24:27], 'little') + 1
                height = int.from_bytes(head[27:30], 'little') + 1
            elif kind == b'VP8 ' and head[23:26] == b'\x9d\x01\x2a':
                width = int.from_bytes(head[26:28], 'little') & 0x3fff
                height = int.from_bytes(head[28:30], 'little') & 0x3fff
            elif kind == b'VP8L' and head[20:21] == b'\x2f':
                b0, b1, b2, b3 = head[21:25]
                width = 1 + b0 + ((b1 & 0x3f) << 8)
                height = 1 + ((b1 >> 6) & 0x03) + (b2 << 2) + ((b3 & 0x0f) << 10)
            else:
                raise ValueError(f'Unsupported WebP image: {path}')
        elif head[:2] == b'\xff\xd8':
            width = height = 0
            f.seek(2)
            while marker := f.read(1):
                if marker != b'\xff':
                    continue
                marker = f.read(1)
                while marker == b'\xff': marker = f.read(1)
                if not marker or marker in (b'\xd9', b'\xda'):
                    break
                length = int.from_bytes(f.read(2), 'big')
                if length < 2:
                    raise ValueError(f'Invalid JPEG segment: {path}')
                if marker[0] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    data = f.read(5)
                    if len(data) == 5:
                        height = int.from_bytes(data[1:3], 'big')
                        width = int.from_bytes(data[3:5], 'big')
                    break
                f.seek(length - 2, 1)
        else:
            raise ValueError(f'Unsupported or corrupt image: {path}')
    if width < 1 or height < 1:
        raise ValueError(f'Could not read image dimensions: {path}')
    return width, height



def safe_destination(value):
    if not isinstance(value, str) or not value.strip() or any(ch in value for ch in ('\\', '\x00', '\r', '\n')):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    if parsed.netloc:
        return bool(parsed.scheme) and valid_web_url(value)
    if parsed.scheme:
        return parsed.scheme == 'mailto' and bool(re.fullmatch(r'mailto:[^\s@]+@[^\s@]+\.[^\s@]+', value, re.I))
    path = Path(unquote(parsed.path))
    return not path.is_absolute() and '..' not in path.parts

def validate(site, artist, nav, home, artworks, pages, documents=None, error=None):
    errors = []
    required = lambda obj, keys, label: errors.extend(
        f'{label} is missing required field: {key}' for key in keys
        if not isinstance(obj.get(key), str) or not obj.get(key).strip()
    )
    required(site, ('site_name', 'url', 'email', 'theme_color'), 'site.json')
    required(artist, ('name', 'professional_name', 'role', 'location', 'practice', 'medium', 'style', 'profile', 'education', 'professional_practice', 'practice_period', 'statement'), 'artist.json')
    if not valid_web_url(site.get('url')) or urlsplit(site.get('url', '')).scheme != 'https':
        errors.append('site.url must be a valid https URL.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', str(site.get('email', ''))):
        errors.append('site.email must be a valid email address.')
    if not isinstance(artworks, list):
        return errors + ['artworks.json must contain an array.']
    slugs = [w.get('slug') for w in artworks if isinstance(w, dict)]
    if len(slugs) != len(artworks): errors.append('Every artwork must be a JSON object.')
    if len(slugs) != len(set(slugs)): errors.append('Artwork slugs must be unique.')
    for i, work in enumerate(artworks):
        if not isinstance(work, dict): continue
        required(work, ('slug', 'title', 'image', 'date', 'dimensions', 'description', 'quote'), f'Artwork #{i+1}')
        slug = work.get('slug', '')
        if slug and not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
            errors.append(f'Invalid artwork slug: {slug}')
        image = safe_file(ROOT / 'images', work.get('image'))
        if image is None or not image.is_file():
            errors.append(f"Missing or unsafe artwork image: {work.get('image')}")
        else:
            try: image_dimensions(image)
            except (OSError, ValueError): errors.append(f"Unsupported or corrupt artwork image: {work.get('image')}")
        try: date.fromisoformat(work.get('date', ''))
        except (TypeError, ValueError): errors.append(f"Invalid date for artwork {slug}: {work.get('date')}")
    known = set(slugs)
    selected_data = home.get('selected', {})
    if not isinstance(selected_data, dict): errors.append('homepage.selected must be an object.')
    selected = selected_data.get('artworks', []) if isinstance(selected_data, dict) else []
    if not isinstance(selected, list): errors.append('homepage.selected.artworks must be an array.')
    else:
        for slug in selected:
            if slug not in known: errors.append(f'Homepage references unknown artwork: {slug}')
    showcases = home.get('showcases', [])
    if not isinstance(showcases, list): errors.append('homepage.showcases must be an array.')
    else:
        for item in showcases:
            if not isinstance(item, dict) or item.get('artwork') not in known:
                errors.append(f"Showcase references unknown artwork: {item.get('artwork') if isinstance(item, dict) else item}")
    assets = site.get('assets', {})
    for key in ('logo', 'artist_image', 'social_image', 'hero_image'):
        path = safe_file(ROOT / 'images', str(assets.get(key, '')).removeprefix('images/')) if isinstance(assets, dict) else None
        if path is None or not path.is_file():
            errors.append(f'site.assets.{key} references a missing or unsafe image.')
        else:
            try: image_dimensions(path)
            except (OSError, ValueError): errors.append(f'site.assets.{key} references an unsupported or corrupt image.')
    hero = home.get('hero', {})
    for key in ('image', 'preload'):
        value = hero.get(key, '') if isinstance(hero, dict) else ''
        if value:
            path = safe_file(ROOT / 'images', value.removeprefix('images/')) if isinstance(value, str) else None
            if path is None or not path.is_file():
                errors.append(f'homepage.hero.{key} references a missing or unsafe image.')
            else:
                try: image_dimensions(path)
                except (OSError, ValueError): errors.append(f'homepage.hero.{key} references an unsupported or corrupt image.')
    for group in ('primary', 'info', 'footer'):
        items = nav.get(group, []) if isinstance(nav, dict) else []
        if not isinstance(items, list):
            errors.append(f'navigation.{group} must be an array.'); continue
        for item in items:
            if not isinstance(item, dict) or not item.get('label') or not item.get('url'):
                errors.append(f'navigation.{group} entries need label and url.'); continue
            url = item['url']
            if not safe_destination(url): errors.append(f'Unsafe navigation URL: {url}')
    socials = site.get('socials', [])
    if not isinstance(socials, list): errors.append('site.socials must be an array.')
    else:
        for social in socials:
            if not isinstance(social, dict) or not social.get('label') or not valid_web_url(social.get('url')):
                errors.append('Every social link needs a label and a valid http(s) URL.')
    if site.get('newsletter_enabled'):
        action = site.get('newsletter_action', '')
        if not valid_web_url(action) or urlsplit(action).scheme != 'https': errors.append('site.newsletter_action must be a valid https URL.')
    for slug, page in pages.items():
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug): errors.append(f'Invalid page slug: {slug}')
        if not isinstance(page, dict) or not page.get('title') or not isinstance(page.get('sections'), list):
            errors.append(f'Page {slug} needs a title and sections array.'); continue
        download = page.get('download', {})
        if download and (not isinstance(download, dict) or safe_file(ROOT, download.get('file', '')) is None or not safe_file(ROOT, download.get('file', '')).is_file()):
            errors.append(f'Page {slug} has an invalid download file path.')
        for section in page['sections']:
            if not isinstance(section, dict):
                errors.append(f'Page {slug} contains a non-object section.'); continue
            link = section.get('link', {}).get('url') if isinstance(section.get('link'), dict) else None
            if link and not safe_destination(link): errors.append(f'Page {slug} has an unsafe link: {link}')
    if not isinstance(home.get('hero'), dict) or not isinstance(home.get('intro'), dict) or not isinstance(home.get('manifesto'), dict) or not isinstance(home.get('about'), dict) or not isinstance(home.get('contact'), dict) or not isinstance(home.get('newsletter'), dict):
        errors.append('homepage.json must include hero, intro, manifesto, about, contact and newsletter objects.')
    elif not isinstance(home['intro'].get('paragraphs'), list): errors.append('homepage.intro.paragraphs must be an array.')
    if not isinstance(site.get('assets'), dict) or not isinstance(site.get('seo'), dict) or not isinstance(site.get('ui'), dict) or not isinstance(site.get('artwork_defaults'), dict):
        errors.append('site.json assets, seo, ui and artwork_defaults must be objects.')
    if not isinstance(error, dict) or not all(key in error for key in ('code', 'title', 'message', 'button')):
        errors.append('error.json needs code, title, message and button fields.')
    if not isinstance(artist.get('biography'), list): errors.append('artist.biography must be an array.')
    if not isinstance(artist.get('skills'), list) or not isinstance(artist.get('software'), list): errors.append('artist.skills and artist.software must be arrays.')
    if documents is not None and not isinstance(documents, dict): errors.append('documents.json must contain an object.')
    if error is not None and not isinstance(error, dict): errors.append('error.json must contain an object.')
    return errors


def build_pdfs(site, artist, artworks, documents):
    out = ROOT / 'files'; out.mkdir(exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Brand', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=24, leading=29, textColor=colors.HexColor('#111111'), spaceAfter=5))
    styles.add(ParagraphStyle(name='SubBrand', parent=styles['Normal'], fontSize=9, leading=13, textColor=colors.HexColor('#666666'), spaceAfter=16))
    styles.add(ParagraphStyle(name='SectionX', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#111111'), spaceBefore=14, spaceAfter=6, keepWithNext=True))
    styles.add(ParagraphStyle(name='BodyX', parent=styles['BodyText'], fontName='Helvetica', fontSize=9, leading=14, textColor=colors.HexColor('#333333'), spaceAfter=7))
    unsupported=set()
    def safe(s):
        s=str(s)
        for ch in s:
            try: ch.encode('cp1252')
            except UnicodeEncodeError: unsupported.add(ch)
        return xml_escape(s).replace('\n','<br/>')
    def make_doc(path, title, story):
        fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.', suffix='.tmp', dir=path.parent)
        os.close(fd)
        temp = Path(temp_name)
        doc = SimpleDocTemplate(str(temp), pagesize=A4, rightMargin=22*mm, leftMargin=22*mm, topMargin=20*mm, bottomMargin=20*mm, title=title, author=artist['name'])
        def footer(canvas, doc):
            canvas.saveState(); canvas.setFont('Helvetica', 8); canvas.setFillColor(colors.HexColor('#777777'))
            canvas.drawString(22*mm, 12*mm, f"{site['site_name']}  ·  {site['url']}")
            canvas.drawRightString(A4[0]-22*mm, 12*mm, f"{doc.page}")
            canvas.restoreState()
        try:
            doc.build(story, onFirstPage=footer, onLaterPages=footer)
            os.chmod(temp, 0o644)
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)
    def header(title, subtitle): return [Paragraph(safe(title), styles['Brand']), Paragraph(safe(subtitle), styles['SubBrand']), HRFlowable(width='100%', thickness=0.7, color=colors.HexColor('#222222')), Spacer(1,8)]
    selected = artworks
    # CV
    s = header(documents.get('cv', {}).get('title', 'CURRICULUM VITAE').upper(), artist['professional_name'])
    s += [Paragraph(safe(f"{artist['name']} · {artist['location']}"), styles['BodyX']), Paragraph(safe(f"{site['email']} · {site['url']}"), styles['BodyX'])]
    for heading, text in [('ARTIST PROFILE',artist['profile']),('PRACTICE',artist['practice']),('MEDIUM',artist['medium']),('EDUCATION',artist['education']),('PROFESSIONAL PRACTICE',f"{artist['professional_practice']} · {artist['practice_period']}")]:
        s += [Paragraph(heading,styles['SectionX']),Paragraph(safe(text),styles['BodyX'])]
    for heading, items in [('SKILLS',artist['skills']),('SOFTWARE',artist['software']),('SELECTED WORKS',[w['title'] for w in selected])]:
        s.append(Paragraph(heading,styles['SectionX']))
        for item in items: s.append(Paragraph('•  '+safe(item),styles['BodyX']))
    make_doc(out/'cv.pdf','INKTENEBRIS — CV',s)
    # Statement
    s = header(documents.get('statement', {}).get('title', 'ARTIST STATEMENT').upper(), artist['professional_name']) + [Paragraph(safe(artist['statement']),styles['BodyX'])]
    make_doc(out/'statement.pdf','INKTENEBRIS — Artist Statement',s)
    # Press kit
    s = header(documents.get('press_kit', {}).get('title', 'PRESS KIT').upper(), f"{artist['professional_name']} · {artist['practice']}")
    contact_lines = [f"Artist: {artist['name']}", f"Location: {artist['location']}", f"Website: {site['url']}", f"Email: {site['email']}"]
    facts_lines = [f"Artist: {artist['name']}", f"Artist name: {artist['professional_name']}", f"Location: {artist['location']}", f"Medium: {artist['medium']}", f"Style: {artist['style']}"]
    s += [Paragraph('<br/>'.join(map(safe, contact_lines)),styles['BodyX']),Paragraph('ARTIST OVERVIEW',styles['SectionX']),Paragraph(safe(artist['profile']),styles['BodyX']),Paragraph('ARTIST STATEMENT',styles['SectionX']),Paragraph(safe(artist['statement']),styles['BodyX']),Paragraph('QUICK FACTS',styles['SectionX']),Paragraph('<br/>'.join(map(safe, facts_lines)),styles['BodyX']),Paragraph('SELECTED WORKS',styles['SectionX'])]
    for i,w in enumerate(selected,1): s.append(Paragraph(f"{i:02d} — <b>{safe(w['title'])}</b><br/>{safe(w['description'])}",styles['BodyX']))
    contact = [site['email'], ' · '.join(x['url'] for x in site.get('socials', []))]
    s += [Paragraph('CONTACT', styles['SectionX']), Paragraph('<br/>'.join(map(safe, contact)), styles['BodyX'])]
    make_doc(out/'press-kit.pdf','INKTENEBRIS — Press Kit',s)
    if unsupported:
        print('WARNING: PDFs use Helvetica, which cannot draw these characters (they will show as boxes): ' + ' '.join(sorted(unsupported)), file=sys.stderr)


def main():
    site=load_json('site.json'); artist=load_json('artist.json'); nav=load_json('navigation.json'); home=load_json('homepage.json'); artworks=load_json('artworks.json'); pages=load_json('pages.json'); documents=load_json('documents.json'); error=load_json('error.json')
    errors=validate(site,artist,nav,home,artworks,pages,documents,error)
    if errors:
        print('BUILD FAILED — content validation errors:')
        for e in errors: print(' - '+e)
        sys.exit(1)
    for folder in ('pages', 'legal', 'artworks', 'files'):
        directory = ROOT / folder
        directory.mkdir(mode=0o755, exist_ok=True)
        os.chmod(directory, 0o755)
    env=Environment(loader=FileSystemLoader(str(TEMPLATES)),autoescape=select_autoescape(['html','xml']))
    env.filters['tojson']=json_for_html
    env.filters['linebreaks']=safe_linebreaks
    token = re.compile(r'\{\{\s*(site|artist)\.([A-Za-z_]\w*)\s*\}\}')
    def render_text(value):
        def replace(match):
            source = site if match.group(1) == 'site' else artist
            result = source.get(match.group(2), '')
            return str(result) if isinstance(result, (str, int, float)) else ''
        return token.sub(replace, str(value))
    year=str(date.today().year) if site.get('copyright_year')=='auto' else str(site.get('copyright_year'))
    schema={'@context':'https://schema.org','@type':'VisualArtist','name':artist['name'],'alternateName':artist['professional_name'],'image':site['url']+'/'+site['assets']['artist_image'],'url':site['url'],'jobTitle':artist['role'],'description':site['seo']['description'],'genre':artist['style'],'sameAs':[x['url'] for x in site.get('socials',[])]}
    base_context=dict(site=site,artist=artist,navigation=nav,year=year,schema=schema,social_image=site['assets'].get('social_image','images/logo.png'),description=site['seo']['description'],preload_image=home['hero'].get('preload',''),is_home=False)
    # Homepage
    lookup={w['slug']:w for w in artworks}
    def with_size(work):
        w,h=image_dimensions(ROOT/'images'/work['image']); return {**work,'width':w,'height':h}
    showcases=[]
    for item in home['showcases']:
        showcases.append({**with_size(lookup[item['artwork']]),'showcase_description':item['description']})
    selected=[lookup[s] for s in home['selected']['artworks']]
    selected_sized=[with_size(w) for w in selected]
    hero_w,hero_h=image_dimensions(safe_file(ROOT,home['hero']['image']))
    artist_w,artist_h=image_dimensions(safe_file(ROOT,site['assets']['artist_image']))
    home_body=env.get_template('home.html').render(home=home,showcases=showcases,selected_works=selected_sized,artist=artist,site=site,hero_size=(hero_w,hero_h),artist_size=(artist_w,artist_h))
    ctx={**base_context,'base':'','title':site['site_name'],'canonical':site['url']+'/','is_home':True,'body':home_body,'preload_image':home['hero'].get('preload','')}
    save_text(ROOT/'index.html',env.get_template('base.html').render(**ctx))
    # Static content pages
    for slug,page in pages.items():
        path_prefix='../'
        folder='legal' if slug in ('privacy','terms') else 'pages'
        canonical_path=f'{folder}/{slug}.html'
        rendered_page={**page,'subtitle':render_text(page.get('subtitle',''))}
        body=env.get_template('content_page.html').render(page=rendered_page,selected_works=selected,artist=artist,site={**site,'policy_updated':site.get('policy_updated','')},documents=documents,base=path_prefix,render_text=render_text)
        desc=page.get('meta_description') or site['seo']['description']
        ctx={**base_context,'base':path_prefix,'title':page['title'],'canonical':site['url']+'/'+canonical_path,'description':desc,'body':body,'preload_image':''}
        save_text(ROOT/canonical_path,env.get_template('base.html').render(**ctx))
    # Artwork detail pages
    for i,work in enumerate(artworks):
        image=ROOT/'images'/work['image']; width,height=image_dimensions(image)
        work_render={**work,'width':width,'height':height,'date_display':date.fromisoformat(work['date']).strftime('%d %B %Y').upper()}
        body=env.get_template('artwork.html').render(base='../',work=work_render,index=i+1,previous=artworks[i-1] if i else None,next_work=artworks[i+1] if i+1<len(artworks) else None,artist=artist,site=site)
        ctx={**base_context,'base':'../','title':work['title'],'canonical':site['url']+f"/artworks/{work['slug']}.html",'description':f"{work['title']}. {work['description']}",'social_image':'images/'+work['image'],'body':body,'preload_image':''}
        save_text(ROOT/'artworks'/f"{work['slug']}.html",env.get_template('base.html').render(**ctx))
    # Sitemap includes every generated public HTML page.
    # lastmod is only emitted where it is truthful (an artwork's own date); a build date would claim every page changed on every build.
    urls=[('',None),*[(f"artworks/{w['slug']}.html",w['date']) for w in artworks],*[(f"pages/{s}.html",None) for s in pages if s not in ('privacy','terms')],('legal/privacy.html',None),('legal/terms.html',None)]
    sitemap='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{xml_escape(site["url"]+("/"+p if p else "/"))}</loc>'+(f'<lastmod>{d}</lastmod>' if d else '')+'<changefreq>monthly</changefreq></url>\n' for p,d in urls)+'</urlset>\n'
    save_text(ROOT/'sitemap.xml',sitemap)
    imgs='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
    for w in artworks: imgs+=f'<url><loc>{xml_escape(site["url"]+"/artworks/"+w["slug"]+".html")}</loc><image:image><image:loc>{xml_escape(site["url"]+"/images/"+w["image"])}</image:loc><image:title>{xml_escape(w["title"])}</image:title></image:image></url>\n'
    save_text(ROOT/'sitemap-images.xml',imgs+'</urlset>')
    error_message=Markup('<br />').join(escape(line) for line in str(error['message']).split('\n'))
    save_text(ROOT/'404.html',env.get_template('404.html').render(site=site,error=error,error_message=error_message))
    build_pdfs(site,artist,artworks,documents)
    active_pages = {ROOT / 'index.html', ROOT / '404.html'}
    active_pages.update(ROOT / ('legal' if slug in ('privacy', 'terms') else 'pages') / f'{slug}.html' for slug in pages)
    active_pages.update(ROOT / 'artworks' / f"{work['slug']}.html" for work in artworks)
    for folder in ('pages', 'legal', 'artworks'):
        for stale in (ROOT / folder).glob('*.html'):
            if stale not in active_pages:
                stale.unlink()
    print(f"Built {2+len(artworks)+len(pages)} HTML pages, 2 sitemaps and 3 PDFs.")
    print('All content validation checks passed.')

if __name__=='__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f'BUILD FAILED — {exc}', file=sys.stderr)
        sys.exit(1)
