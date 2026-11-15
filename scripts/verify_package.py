"""Verify ZIP checksums, then self-test its extracted executable with a clean PATH."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vedaboat import APP_NAME, ARCHIVE_NAME, __version__


def main():
    archive = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "release" / f"{ARCHIVE_NAME}-{__version__}-Local-Review-Windows-x64.zip"
    target = ROOT / "qa" / f"Portable {__version__} copy తెలుగు"
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError("ZIP CRC failure: " + bad)
        manifest = json.loads(z.read(APP_NAME+"/checksums.json"))
        for name, expected in manifest.items():
            digest = hashlib.sha256(z.read(APP_NAME+"/" + name)).hexdigest()
            if digest != expected:
                raise RuntimeError("Package checksum mismatch: " + name)
        for item in z.infolist():
            if not (target / item.filename).resolve().is_relative_to(target.resolve()):
                raise RuntimeError("Unsafe archive member")
        z.extractall(target)
    print(f"ZIP CRC and {len(manifest)} file hashes verified", flush=True)
    report = target / "frozen-self-test.json"
    env = os.environ.copy()
    env["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32") + ";" + os.environ["SystemRoot"]
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    process = subprocess.run([str(target / APP_NAME / (APP_NAME+".exe")), "--self-test", str(report), "--network"], env=env,
                              cwd=target, timeout=180, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    result = json.loads(report.read_text(encoding="utf-8"))
    print(json.dumps(result, ensure_ascii=True, indent=2), flush=True)
    if process.returncode or not all(r["ok"] for r in result.values()):
        raise RuntimeError("Frozen runtime verification failed")
    print("Extracted app passes with a clean PATH and a Unicode/spaced package path", flush=True)


if __name__ == "__main__":
    main()
