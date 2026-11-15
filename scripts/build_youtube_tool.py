"""Build yt-dlp from pinned Python packages without optional GPL dependencies."""
import importlib.metadata as metadata
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    for name, expected in (('yt-dlp', '2026.10.26'), ('yt-dlp-ejs', '0.8.0')):
        if metadata.version(name) != expected:
            raise RuntimeError(f'Install the recorded {name}=={expected} build dependency.')
    output = ROOT / 'vendor' / 'portable-tools' / 'youtube'
    stage = ROOT / 'vendor' / 'portable-tools' / 'output'
    stage.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
               '--console', '--name', 'yt-dlp', '--distpath', str(output),
               '--workpath', str(ROOT / 'build' / 'youtube-work'),
               '--specpath', str(ROOT / 'build'), '--collect-submodules', 'yt_dlp',
               '--collect-all', 'yt_dlp_ejs', '--copy-metadata', 'yt-dlp',
               '--copy-metadata', 'yt-dlp-ejs']
    for name in ('mutagen', 'Crypto', 'Cryptodome', 'websockets', 'brotli', 'brotlicffi',
                 'curl_cffi', 'secretstorage', 'PIL', 'pytest', 'numpy', 'tkinter'):
        command += ['--exclude-module', name]
    policy = Path(sys.base_prefix) / 'Lib' / 'codex-rejected-cas.pem'
    if policy.exists():
        command += ['--add-data', str(policy) + ';.']
    command.append(str(ROOT / 'scripts' / 'youtube_entry.py'))
    subprocess.run(command, check=True, cwd=ROOT)
    shutil.copy2(output / 'yt-dlp.exe', stage / 'yt-dlp.exe')
    subprocess.run([str(stage / 'yt-dlp.exe'), '--version'], check=True,
                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


if __name__ == '__main__':
    main()
