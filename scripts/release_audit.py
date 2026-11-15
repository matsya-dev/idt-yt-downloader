"""Export only reviewed project files; audit source/package privacy and checksums."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vedaboat import ARCHIVE_NAME, __version__

ROOT_FILES = (
    '.gitignore', '.gitattributes', 'README.md', 'LICENSE.txt', 'Instructions.txt',
    'Release notes.txt', 'PRIVACY.md', 'CONTRIBUTING.md', 'DISTRIBUTION_STATUS.txt',
    'requirements.txt', 'requirements-dev.txt', 'pytest.ini', 'run.py',
    'requirements-lock.txt',
)
SCRIPTS = (
    'app_icon.svg', 'build.py', 'fetch_tools.py', 'make_icon.py', 'live_check.py',
    'live_download_check.py', 'verify_package.py', 'release_audit.py',
    'build_audio_tools.sh', 'build_youtube_tool.py', 'youtube_entry.py',
    'prepare_dependencies.py', 'collect_licenses.py', 'verify_portable.py',
    'ci_windows_check.py',
)
TEXT_SUFFIXES = {'.py', '.md', '.txt', '.json', '.yml', '.yaml', '.svg', '.ini'}
SECRET_PATTERNS = (
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    re.compile(r'\bgithub_pat_[A-Za-z0-9_]{40,}\b'),
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{35,}\b'),
)


def source_files(root: Path):
    """An explicit allowlist keeps local work/history out of a public upload."""
    paths = [root / name for name in ROOT_FILES]
    paths += [root / 'scripts' / name for name in SCRIPTS]
    for folder in ('vedaboat', 'tests', 'docs', '.github', 'third-party'):
        paths += [p for p in (root / folder).rglob('*') if p.is_file()
                  and '__pycache__' not in p.parts and p.suffix != '.pyc']
    paths += [p for p in (root / 'assets').rglob('*') if p.is_file()
              and not p.name.startswith('vedaboat.')]
    paths += [root / 'tools' / 'versions.json']
    return sorted(set(paths))


def check_member(name: str, data: bytes):
    """Reject unintended payloads without printing any matched secret material."""
    path = PurePosixPath(name)
    errors = []
    if '\\' in name or path.is_absolute() or '..' in path.parts or re.match(r'^[A-Za-z]:', name):
        errors.append('unsafe archive path')
    if any(p.lower() in {'.git', '.venv', '__pycache__', '.pytest_cache', 'qa', '.vedaboat'}
           for p in path.parts):
        errors.append('local work/profile directory')
    lower = path.name.lower()
    if (lower.startswith('.env') or lower.endswith(('.sqlite3', '.sqlite3-wal',
            '.sqlite3-shm', '.db', '.part', '.mp3', '.wav', '.m4a', '.webm', '.mp4', '.log', '.pyc'))
            or lower in {'id_rsa', 'id_ed25519', '.git-credentials'}):
        errors.append('profile, credentials, downloaded media or test output')
    if path.suffix.lower() in TEXT_SUFFIXES or lower in {'.gitignore', '.gitattributes'}:
        body = data.decode('utf-8', errors='replace')
        if any(pattern.search(body) for pattern in SECRET_PATTERNS):
            errors.append('possible credential/private key; inspect privately')
        if re.search(r'[A-Za-z]:[\\/]Users[\\/](?!Public\b)[^\\/\s]+', body, re.I):
            errors.append('absolute personal Windows path')
    return errors


def audit_archive(archive: Path, *, portable=False):
    errors = []
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            errors.append('ZIP CRC failure')
        names = [i.filename for i in z.infolist() if not i.is_dir()]
        if len(names) != len(set(names)):
            errors.append('duplicate ZIP members')
        for name in names:
            for reason in check_member(name, z.read(name)):
                errors.append(f'{name}: {reason}')
        if portable:
            manifest_name = next(n for n in names if n.count('/') == 1 and n.endswith('/checksums.json'))
            prefix = manifest_name.rsplit('/', 1)[0] + '/'
            manifest = json.loads(z.read(manifest_name))
            expected = {prefix + n for n in manifest}
            if expected != set(names) - {manifest_name}:
                errors.append('manifest does not cover the exact archive file set')
            for name, digest in manifest.items():
                if prefix + name in names and hashlib.sha256(z.read(prefix + name)).hexdigest() != digest:
                    errors.append(f'{name}: SHA256 mismatch')
    return dict(archive=archive.name, files=len(names), bytes=archive.stat().st_size,
                sha256=hashlib.sha256(archive.read_bytes()).hexdigest(), errors=errors,
                passed=not errors,
                limits='Pattern-based local privacy audit; not a full security or legal certification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, help='Also audit an existing portable ZIP.')
    args = parser.parse_args()
    output = ROOT / 'release'
    output.mkdir(exist_ok=True)
    archive = output / f'{ARCHIVE_NAME}-{__version__}-Source.zip'
    prefix = f'{ARCHIVE_NAME}-{__version__}-Source'
    paths = source_files(ROOT)
    findings = [(p.relative_to(ROOT).as_posix(), check_member(p.relative_to(ROOT).as_posix(), p.read_bytes()))
                for p in paths]
    failed = [(n, e) for n, e in findings if e]
    if failed:
        raise RuntimeError('Source audit failed: ' + json.dumps(failed))
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in paths:
            z.write(p, prefix + '/' + p.relative_to(ROOT).as_posix())
    report = {'source': audit_archive(archive)}
    if args.package:
        report['portable'] = audit_archive(args.package, portable=True)
    (output / 'source-audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    archive.with_suffix('.zip.sha256').write_text(report['source']['sha256'] + '  ' + archive.name + '\n', encoding='ascii')
    print(json.dumps(report, indent=2))
    return 0 if all(r['passed'] for r in report.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
