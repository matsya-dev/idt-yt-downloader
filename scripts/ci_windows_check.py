"""Verify the exact draft-release artifacts on a clean GitHub Windows runner."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
import platform
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    config = json.loads((ROOT / '.github' / 'release-candidate.json').read_text())
    release = ROOT / 'release'
    release.mkdir(exist_ok=True)
    session = requests.Session()
    session.headers.update({'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                            'Accept': 'application/octet-stream'})
    for asset in config['assets']:
        response = session.get(f"https://api.github.com/repos/matsya-dev/idt-yt-downloader/releases/assets/{asset['id']}", timeout=(15, 180))
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != asset['sha256']:
            raise RuntimeError('Candidate asset hash mismatch: ' + asset['name'])
        (release / asset['name']).write_bytes(response.content)
        print('Verified downloaded asset:', asset['name'], flush=True)
    archive = next(release.glob('*-Windows-x64.zip'))
    manifest = json.loads((ROOT / 'tools' / 'versions.json').read_text())
    with zipfile.ZipFile(archive) as z:
        for name, record in manifest.items():
            member = 'IDT-YT Downloader/_internal/tools/' + name
            data = z.read(member)
            if hashlib.sha256(data).hexdigest() != record['sha256']:
                raise RuntimeError('Candidate tool mismatch: ' + name)
            (ROOT / 'tools' / name).write_bytes(data)
    sources = next(release.glob('*-Dependency-Sources.zip'))
    with zipfile.ZipFile(sources) as z:
        names = {n for n in z.namelist() if not n.endswith('/')}
        key = next(n for n in names if n.endswith('/checksums.json'))
        prefix = key.rsplit('/', 1)[0] + '/'
        entries = json.loads(z.read(key))
        if {prefix + n for n in entries} != names - {key}:
            raise RuntimeError('Source manifest file set mismatch')
        for name, digest in entries.items():
            if hashlib.sha256(z.read(prefix + name)).hexdigest() != digest:
                raise RuntimeError('Dependency source mismatch: ' + name)
        print('Verified dependency-source files:', len(entries), flush=True)
    (ROOT / 'qa').mkdir(exist_ok=True)
    subprocess.run([sys.executable, '-m', 'pytest', '-q', '--junitxml', str(ROOT / 'qa' / 'ci-pytest.xml')], check=True, cwd=ROOT)
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'verify_portable.py'), '--network',
                    '--output', str(ROOT / 'qa' / 'ci-verification.json')], check=True, cwd=ROOT)
    result_path = ROOT / 'qa' / 'ci-verification.json'
    result = json.loads(result_path.read_text())
    suites = ET.parse(ROOT / 'qa' / 'ci-pytest.xml').getroot().iter('testsuite')
    suites = list(suites)
    result['test_suite'] = {key: sum(int(s.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
    result['environment'] = dict(platform=platform.platform(), python=platform.python_version())
    result_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
