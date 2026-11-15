"""Archive the exact source inputs and notices for the distributable tool set."""
from __future__ import annotations
import hashlib
import importlib.metadata as metadata
import json
import shutil
import subprocess
import sys
import tarfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'vendor' / 'dependency-sources'
NOTICES = ROOT / 'third-party'
FFMPEG_COMMIT = 'd838f9f9aeb0e09b4d068e2af20a46a12640696f'
PACKAGES = ('yt-dlp', 'yt-dlp-ejs', 'requests', 'beautifulsoup4', 'soupsieve',
            'urllib3', 'certifi', 'charset-normalizer', 'idna', 'typing-extensions',
            'setuptools', 'pyinstaller', 'packaging')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url, path, expected=None):
    if not path.exists() or (expected and digest(path) != expected):
        response = requests.get(url, timeout=(15, 90))
        response.raise_for_status()
        path.write_bytes(response.content)
    if expected and digest(path) != expected:
        raise RuntimeError('Source checksum mismatch: ' + path.name)
    return digest(path)


def pypi_source(name):
    version = metadata.version(name)
    response = requests.get(f'https://pypi.org/pypi/{name}/{version}/json', timeout=30)
    response.raise_for_status()
    artifact = next(x for x in response.json()['urls'] if x['packagetype'] == 'sdist')
    sha = fetch(artifact['url'], CACHE / artifact['filename'], artifact['digests']['sha256'])
    return dict(component=name, version=version, filename=artifact['filename'],
                url=artifact['url'], sha256=sha)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    NOTICES.mkdir(exist_ok=True)
    work = ROOT / 'vendor' / 'portable-tools'
    work.mkdir(exist_ok=True)
    compiler = work / 'w64devkit-x64-2.11.0.7z.exe'
    compiler_url = 'https://github.com/skeeto/w64devkit/releases/download/v2.11.0/w64devkit-x64-2.11.0.7z.exe'
    compiler_sha = '54c2bb9962e8a30c8270e34c5efc3d5fee579f53087fa7d435b95fbba2af7b2b'
    fetch(compiler_url, compiler, compiler_sha)
    if not (work / 'w64devkit' / 'bin' / 'gcc.exe').exists():
        subprocess.run([str(compiler), '-y', '-o' + str(work)], check=True,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    fixed = [
        ('FFmpeg', FFMPEG_COMMIT, 'FFmpeg-' + FFMPEG_COMMIT + '.tar.gz',
         f'https://api.github.com/repos/FFmpeg/FFmpeg/tarball/{FFMPEG_COMMIT}',
         'c448f901caf3c03cc5c3ef12c4b79cb4f8794ad5c73239fa185f4993c8f755c2',
         ROOT / 'qa' / 'release-readiness' / ('FFmpeg-' + FFMPEG_COMMIT + '.tar.gz')),
        ('LAME', '3.100', 'lame-3.100.tar.gz',
         'https://downloads.sourceforge.net/project/lame/lame/3.100/lame-3.100.tar.gz',
         'ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e',
         ROOT / 'vendor' / 'portable-tools' / 'lame-3.100.tar.gz'),
        ('QuickJS-NG', 'v0.18.0', 'QuickJS-v0.18.0.tar.gz',
         'https://api.github.com/repos/quickjs-ng/quickjs/tarball/v0.18.0',
         '6e6f84e3ead8592e1694a67a0993c809204889e67d1ed59a0beda2591f7f6c9b',
         ROOT / 'qa' / 'release-readiness' / 'QuickJS-v0.18.0.tar.gz'),
    ]
    records = []
    for name, version, filename, url, sha, local in fixed:
        dest = CACHE / filename
        if not dest.exists() and local.exists():
            shutil.copy2(local, dest)
        fetch(url, dest, sha)
        records.append(dict(component=name, version=version, filename=filename, url=url, sha256=sha))
    if not (work / 'lame-3.100').exists():
        with tarfile.open(CACHE / 'lame-3.100.tar.gz') as archive:
            archive.extractall(work, filter='data')
    ffmpeg = work / 'ffmpeg-source'
    if not ffmpeg.exists():
        ffmpeg.mkdir()
        with tarfile.open(CACHE / ('FFmpeg-' + FFMPEG_COMMIT + '.tar.gz')) as archive:
            archive.extractall(ffmpeg, filter='data')
    with ThreadPoolExecutor(max_workers=4) as pool:
        records += list(pool.map(pypi_source, PACKAGES))
    license_urls = {
        'Tcl-license.txt': 'https://raw.githubusercontent.com/tcltk/tcl/core-8-6-12/license.terms',
        'Python-Windows-CRT-license.txt': 'https://raw.githubusercontent.com/python/cpython/v3.12.14/PC/crtlicense.txt',
        'Tk-license.txt': 'https://raw.githubusercontent.com/tcltk/tk/core-8-6-12/license.terms',
        'OpenSSL-license.txt': 'https://raw.githubusercontent.com/openssl/openssl/openssl-3.5.8/LICENSE.txt',
        'GCC-runtime-exception.txt': 'https://raw.githubusercontent.com/gcc-mirror/gcc/releases/gcc-16.2.0/COPYING.RUNTIME',
        'libffi-license.txt': 'https://raw.githubusercontent.com/libffi/libffi/v3.4.4/LICENSE',
        'zlib-license.txt': 'https://raw.githubusercontent.com/madler/zlib/v1.3.2/LICENSE',
        'Expat-license.txt': 'https://raw.githubusercontent.com/libexpat/libexpat/R_2_8_3/expat/COPYING',
    }
    for name, url in license_urls.items():
        fetch(url, NOTICES / name)
    shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', NOTICES / 'Python-license.txt')
    shutil.copy2(ROOT / 'vendor' / 'portable-tools' / 'w64devkit' / 'COPYING.MinGW-w64-runtime.txt', NOTICES / 'MinGW-runtime-license.txt')
    with tarfile.open(CACHE / 'lame-3.100.tar.gz') as t:
        NOTICES.joinpath('LAME-license.txt').write_bytes(t.extractfile('lame-3.100/COPYING').read())
    toolchain = dict(version='w64devkit 2.11.0 / GCC 16.2.0', url=compiler_url, sha256=compiler_sha,
                     source='https://github.com/skeeto/w64devkit/releases/tag/v2.11.0',
                     distributed=False)
    (NOTICES / 'sources.json').write_text(json.dumps(dict(sources=records, build_toolchain=toolchain), indent=2) + '\n', encoding='utf8')
    print('Archived and verified', len(records), 'matching source distributions.')


if __name__ == '__main__':
    main()
