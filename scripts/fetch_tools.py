"""Fetch exactly the recorded runtime tools; verify every extracted tool hash."""
from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tools=ROOT/'tools';cache=ROOT/'vendor';cache.mkdir(exist_ok=True);tools.mkdir(exist_ok=True)
    manifest=json.loads((tools/'versions.json').read_text(encoding='utf8'))
    archives={}
    for name,rec in manifest.items():
        path=tools/name
        if path.exists() and sha256(path)==rec['sha256']:continue
        if 'archive_member' in rec:
            if rec['url'] not in archives:
                r=requests.get(rec['url'],timeout=(15,120));r.raise_for_status()
                archive=cache/'recorded-release-tools.zip';archive.write_bytes(r.content);archives[rec['url']]=archive
            with zipfile.ZipFile(archives[rec['url']]) as z:data=z.read(rec['archive_member'])
        else:
            r=requests.get(rec['url'],timeout=(15,90));r.raise_for_status();data=r.content
        if hashlib.sha256(data).hexdigest()!=rec['sha256']:raise RuntimeError('Recorded tool checksum mismatch: '+name)
        temp=path.with_suffix('.download');temp.write_bytes(data);temp.replace(path)
    print('All recorded runtime tool hashes verified.')


if __name__=='__main__':main()
