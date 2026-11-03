#!/usr/bin/env python3
"""Stage public files and atomically replace the GitHub Pages package."""
from pathlib import Path
import os
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'


def main():
    staging = Path(tempfile.mkdtemp(prefix='.dist-staging-', dir=ROOT))
    backup = ROOT / f'.dist-backup-{os.getpid()}'
    try:
        files = ('index.html', '404.html', 'robots.txt', 'sitemap.xml', 'sitemap-images.xml',
                 'site.webmanifest', 'ads.txt', 'humans.txt', 'llms.txt',
                 'BingSiteAuth.xml', 'google1e2fb5dab450565c.html')
        folders = ('assets', 'images', 'artworks', 'pages', 'legal', 'files', '.well-known')
        for name in files:
            source = ROOT / name
            if source.is_file():
                shutil.copy2(source, staging / name)
        for name in folders:
            source = ROOT / name
            if source.is_dir():
                shutil.copytree(source, staging / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        os.chmod(staging, 0o755)
        for item in staging.rglob('*'):
            os.chmod(item, 0o755 if item.is_dir() else 0o644)
        if backup.exists():
            shutil.rmtree(backup)
        if DIST.exists():
            os.replace(DIST, backup)
        try:
            os.replace(staging, DIST)
        except Exception:
            if backup.exists():
                os.replace(backup, DIST)
            raise
        if backup.exists():
            shutil.rmtree(backup)
        print(f'Packaged public website into {DIST.relative_to(ROOT)}/')
    finally:
        if staging.exists():
            shutil.rmtree(staging)


if __name__ == '__main__':
    main()
