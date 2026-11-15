import importlib.util
import json
import hashlib
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location('release_audit', Path(__file__).parents[1] / 'scripts' / 'release_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_export_excludes_personal_and_historical_files(tmp_path):
    for name in ('vedaboat/app.py', 'vedaboat/__pycache__/app.pyc', 'assets/app-icon.png',
                 'assets/vedaboat.ico', 'qa/profile.sqlite3', 'tools/yt-dlp.exe',
                 'scripts/icon_concepts.py', 'NEXT_VERSION.md'):
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'test')
    exported = {p.relative_to(tmp_path).as_posix() for p in audit.source_files(tmp_path)}
    assert 'vedaboat/app.py' in exported and 'assets/app-icon.png' in exported
    assert not exported & {'vedaboat/__pycache__/app.pyc', 'assets/vedaboat.ico',
                           'qa/profile.sqlite3', 'tools/yt-dlp.exe',
                           'scripts/icon_concepts.py', 'NEXT_VERSION.md'}


def test_audit_rejects_payloads_without_exposing_secrets():
    assert audit.check_member('../outside.txt', b'hello')
    assert audit.check_member('app/qa/test.mp3', b'audio')
    assert audit.check_member('app/.env', b'data')
    credential = 'ghp_' + 'x' * 36
    reasons = audit.check_member('app/config.py', credential.encode())
    assert reasons and credential not in str(reasons)
    assert audit.check_member('README.md', b'C:\\Users\\ExamplePerson\\private')
    assert not audit.check_member('README.md', b'%LOCALAPPDATA%\\VedaBoat')


def test_portable_audit_rejects_unmanifested_and_changed_members(tmp_path):
    package = tmp_path / 'test.zip'
    with zipfile.ZipFile(package, 'w') as z:
        z.writestr('App/Instructions.txt', 'changed')
        z.writestr('App/extra.txt', 'unlisted')
        z.writestr('App/checksums.json', json.dumps({'Instructions.txt': hashlib.sha256(b'original').hexdigest()}))
    result = audit.audit_archive(package, portable=True)
    assert not result['passed']
    assert any('exact archive file set' in e for e in result['errors'])
    assert any('SHA256 mismatch' in e for e in result['errors'])
