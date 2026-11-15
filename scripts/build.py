"""Build and zip a self-contained Windows x64 app with editable source."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vedaboat import APP_NAME, ARCHIVE_NAME, __version__
from release_audit import source_files


def main():
    os.chdir(ROOT)
    if sys.platform != "win32":
        raise SystemExit("Build the Windows package on Windows x64.")
    for tool in ("ffmpeg.exe", "ffprobe.exe", "yt-dlp.exe", "qjs.exe"):
        if not (ROOT / "tools" / tool).exists():
            raise SystemExit("Missing " + tool + ". Run scripts/fetch_tools.py first.")
    local_tcl = ROOT / "vendor" / "tcl"
    env = os.environ.copy()
    if local_tcl.exists():
        env["TCL_LIBRARY"] = str(local_tcl / "tcl8.6")
        env["TK_LIBRARY"] = str(local_tcl / "tk8.6")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "make_icon.py")], check=True)
    extra_data = []
    # This managed Python runtime's ssl.py loads an additional CA policy file.
    # Keep that policy intact in the frozen runtime instead of weakening TLS.
    ssl_policy = Path(sys.base_prefix) / "Lib" / "codex-rejected-cas.pem"
    if ssl_policy.exists():
        extra_data += ["--add-data", str(ssl_policy) + ";."]
    # Build in a fresh directory. Never mix stale files/manifests into a package,
    # and never replace an older app directory that someone may still be using.
    dist_root = ROOT / 'dist' / (__version__ + '-review-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
                    "--name", APP_NAME, "--icon", str(ROOT / "assets" / "app-icon.ico"),
                    "--distpath",str(dist_root),
                    "--exclude-module", "pytest", "--exclude-module", "PIL", "--exclude-module", "numpy",
                    "--exclude-module", "matplotlib", "--exclude-module", "IPython", "--exclude-module", "scipy",
                    *extra_data, str(ROOT / "run.py")], check=True, env=env)
    package = dist_root / APP_NAME
    for folder in ("tools", "assets", "third-party"):
        shutil.copytree(ROOT / folder, package / folder, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('vedaboat.*') if folder=='assets' else None)
    notices = package / "third-party"
    for name in ("requests", "beautifulsoup4", "soupsieve", "urllib3", "certifi", "charset-normalizer", "idna", "typing-extensions", "setuptools"):
        dist = metadata.distribution(name)
        for entry in dist.files or []:
            if ".dist-info" in str(entry) and any(p in entry.name.upper() for p in ("LICENSE", "COPYING", "NOTICE")):
                path = dist.locate_file(entry)
                if path.is_file():
                    shutil.copy2(path, notices / (name + "-" + entry.name))
    for name, path in (("Python-LICENSE.txt", Path(sys.base_prefix) / "LICENSE.txt"),
                       ("Tcl-license.terms", local_tcl / "tcl8.6" / "license.terms"),
                       ("Tk-license.terms", local_tcl / "tk8.6" / "license.terms")):
        if path.exists():
            shutil.copy2(path, notices / name)
    for file in ("Instructions.txt", "LICENSE.txt", "Release notes.txt", "PRIVACY.md", "DISTRIBUTION_STATUS.txt"):
        shutil.copy2(ROOT / file, package / file)
    source = package / "source"
    for path in source_files(ROOT):
        target = source / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    qa = ROOT / "qa" / "verification.txt"
    if qa.exists():
        shutil.copy2(qa, package / "Verification.txt")
    manifest = {}
    for path in sorted(package.rglob("*")):
        if path.is_file():
            manifest[path.relative_to(package).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (package / "checksums.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    archive = release / f"{ARCHIVE_NAME}-{__version__}-Local-Review-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                z.write(path, Path(APP_NAME) / path.relative_to(package))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(digest + "  " + archive.name + "\n", encoding="utf-8")
    print(f"Built {archive}\n{archive.stat().st_size / 1024 / 1024:.1f} MB\nSHA256 {digest}")


if __name__ == "__main__":
    main()
