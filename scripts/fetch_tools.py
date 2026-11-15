"""Fetch recorded, hash-verified tools for development on Windows x64.

Uses tools/versions.json rather than silently changing to today's latest release.
Recipients of a portable package need no separate installation.
"""
from __future__ import annotations
import hashlib
import json
import zipfile
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
CACHE = ROOT / 'vendor'
LICENSES = ROOT / 'third-party'


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def download(url, path, digest):
    if not digest or len(digest) != 64:
        raise RuntimeError('A recorded SHA256 is required for ' + path.name)
    if path.exists() and sha256(path) == digest:
        return
    temp = path.with_suffix(path.suffix + '.download')
    print('Fetching', path.name, flush=True)
    try:
        with requests.get(url, stream=True, timeout=(15, 90)) as response:
            response.raise_for_status()
            with temp.open('wb') as out:
                for chunk in response.iter_content(1024 * 1024):
                    out.write(chunk)
        if sha256(temp) != digest:
            raise RuntimeError('Recorded release checksum mismatch: ' + path.name)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def main():
    for p in (TOOLS, CACHE, LICENSES):
        p.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((TOOLS / 'versions.json').read_text(encoding='utf8'))
    for name in ('yt-dlp.exe', 'qjs.exe'):
        rec = manifest[name]
        download(rec['url'], TOOLS / name, rec['sha256'])
    ff = {name: rec for name, rec in manifest.items() if name not in ('yt-dlp.exe', 'qjs.exe')}
    if any(not (TOOLS / name).exists() or sha256(TOOLS / name) != rec['sha256'] for name, rec in ff.items()):
        rec = ff['ffmpeg.exe']
        archive = CACHE / 'ffmpeg-recorded-win64-lgpl.zip'
        download(rec['url'], archive, rec['archive_sha256'])
        with zipfile.ZipFile(archive) as z:
            for name, rec in ff.items():
                member = next(n for n in z.namelist() if n.endswith('/bin/' + name))
                data = z.read(member)
                if hashlib.sha256(data).hexdigest() != rec['sha256']:
                    raise RuntimeError('Recorded component checksum mismatch: ' + name)
                temp = TOOLS / (name + '.download')
                temp.write_bytes(data)
                temp.replace(TOOLS / name)
            # The main upstream LGPL notice is at the archive root, not doc/.
            for member in z.namelist():
                base = Path(member).name
                if not member.endswith('/') and ('LICENSE' in base.upper() or 'COPYING' in base.upper()):
                    (LICENSES / ('FFmpeg-' + base)).write_bytes(z.read(member))
    for name, rec in manifest.items():
        if sha256(TOOLS / name) != rec['sha256']:
            raise RuntimeError('Tool verification failed: ' + name)
    print('All recorded tool hashes verified. Licenses and provenance are in third-party/.')


if __name__ == '__main__':
    main()
