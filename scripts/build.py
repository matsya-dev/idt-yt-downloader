"""Build the single portable EXE, folder ZIP alternative, and matching sources."""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vedaboat import APP_NAME, ARCHIVE_NAME, __version__
from release_audit import source_files
from collect_licenses import collect


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def zip_tree(folder, target, prefix):
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                z.write(path, prefix + '/' + path.relative_to(folder).as_posix())


def main():
    if sys.platform != 'win32':
        raise SystemExit('Build Windows artifacts on Windows x64.')
    os.chdir(ROOT)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    stage = ROOT / 'build' / ('release-' + stamp)
    resources = stage / 'resources'
    resources.mkdir(parents=True)
    manifest = json.loads((ROOT / 'tools' / 'versions.json').read_text(encoding='utf8'))
    (resources / 'tools').mkdir()
    for name, record in manifest.items():
        path = ROOT / 'tools' / name
        if sha256(path) != record['sha256']:
            raise RuntimeError('Recorded tool hash mismatch: ' + name)
        shutil.copy2(path, resources / 'tools' / name)
    shutil.copy2(ROOT / 'tools' / 'versions.json', resources / 'tools' / 'versions.json')
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'make_icon.py')], check=True)
    shutil.copytree(ROOT / 'assets', resources / 'assets', ignore=shutil.ignore_patterns('vedaboat.*'))
    shutil.copytree(ROOT / 'third-party', resources / 'third-party')
    collect(resources / 'third-party')
    for name in ('LICENSE.txt', 'Instructions.txt', 'Release notes.txt', 'PRIVACY.md'):
        shutil.copy2(ROOT / name, resources / name)
    info = dict(name=APP_NAME, version=__version__, format='portable', tools=manifest,
                source_release=f'https://github.com/matsya-dev/idt-yt-downloader/releases/tag/v{__version__}')
    (resources / 'build-info.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf8')
    env = os.environ.copy()
    tcl = ROOT / 'vendor' / 'tcl'
    if tcl.exists():
        env['TCL_LIBRARY'] = str(tcl / 'tcl8.6')
        env['TK_LIBRARY'] = str(tcl / 'tk8.6')
    common = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed',
              '--name', APP_NAME, '--icon', str(ROOT / 'assets' / 'app-icon.ico'),
              '--specpath', str(stage)]
    for name in ('pytest', 'PIL', 'numpy', 'matplotlib', 'IPython', 'scipy', 'yt_dlp', 'yt_dlp_ejs'):
        common += ['--exclude-module', name]
    for path in resources.iterdir():
        common += ['--add-data', str(path) + ';' + (path.name if path.is_dir() else '.')]
    policy = Path(sys.base_prefix) / 'Lib' / 'codex-rejected-cas.pem'
    if policy.exists():
        common += ['--add-data', str(policy) + ';.']
    output = ROOT / 'dist' / (__version__ + '-' + stamp)
    for mode in ('onedir', 'onefile'):
        subprocess.run(common + ['--' + mode, '--distpath', str(output / mode),
                       '--workpath', str(stage / mode), str(ROOT / 'run.py')], check=True, env=env)
    release = ROOT / 'release'
    release.mkdir(exist_ok=True)
    primary = release / f'{ARCHIVE_NAME}-{__version__}-Windows-x64.exe'
    shutil.copy2(output / 'onefile' / (APP_NAME + '.exe'), primary)
    folder = output / 'onedir' / APP_NAME
    for name in ('Instructions.txt', 'Release notes.txt', 'PRIVACY.md', 'LICENSE.txt'):
        shutil.copy2(ROOT / name, folder / name)
    hashes = {p.relative_to(folder).as_posix(): sha256(p) for p in sorted(folder.rglob('*')) if p.is_file()}
    (folder / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf8')
    archive = release / f'{ARCHIVE_NAME}-{__version__}-Windows-x64.zip'
    zip_tree(folder, archive, APP_NAME)
    # Full source inputs for FFmpeg/LAME, the yt-dlp helper and other dependencies.
    source_stage = stage / 'dependency-sources'
    source_stage.mkdir()
    source_records = json.loads((ROOT / 'third-party' / 'sources.json').read_text(encoding='utf8'))
    for record in source_records['sources']:
        path = ROOT / 'vendor' / 'dependency-sources' / record['filename']
        if sha256(path) != record['sha256']:
            raise RuntimeError('Dependency source checksum mismatch: ' + path.name)
        shutil.copy2(path, source_stage / path.name)
    shutil.copy2(ROOT / 'third-party' / 'sources.json', source_stage / 'sources.json')
    (source_stage / 'scripts').mkdir()
    for name in ('build_audio_tools.sh', 'build_youtube_tool.py', 'youtube_entry.py', 'prepare_dependencies.py'):
        shutil.copy2(ROOT / 'scripts' / name, source_stage / 'scripts' / name)
    shutil.copy2(ROOT / 'requirements-lock.txt', source_stage / 'requirements-lock.txt')
    shutil.copy2(ROOT / 'docs' / 'DEPENDENCY_BUILD.md', source_stage / 'BUILD.md')
    shutil.copytree(resources / 'third-party', source_stage / 'licenses')
    dep_hashes = {p.relative_to(source_stage).as_posix(): sha256(p) for p in sorted(source_stage.rglob('*')) if p.is_file()}
    (source_stage / 'checksums.json').write_text(json.dumps(dep_hashes, indent=2) + '\n', encoding='utf8')
    sources = release / f'{ARCHIVE_NAME}-{__version__}-Dependency-Sources.zip'
    zip_tree(source_stage, sources, ARCHIVE_NAME + '-Dependency-Sources')
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'release_audit.py')], check=True)
    artifacts = [primary, archive, sources, release / f'{ARCHIVE_NAME}-{__version__}-Source.zip']
    checksums = ''.join(sha256(p) + '  ' + p.name + '\n' for p in artifacts)
    (release / f'{ARCHIVE_NAME}-{__version__}-SHA256SUMS.txt').write_text(checksums, encoding='ascii')
    print(checksums, flush=True)
    for p in artifacts:
        print(p.name, round(p.stat().st_size / 1024 / 1024, 2), 'MiB', flush=True)
    (release / 'latest-build.json').write_text(json.dumps(dict(version=__version__, folder=str(folder), primary=str(primary), zip=str(archive)), indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
