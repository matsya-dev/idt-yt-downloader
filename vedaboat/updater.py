from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from .engine import atomic_json
from .model import Paused, UserError
from .sources import http_session
from .tools import Tools, run_process


def update_youtube(tools: Tools, report=lambda _: None, cancelled=None) -> str:
    """Stage and verify a complete pair before atomically activating an update."""
    generation = uuid.uuid4().hex
    stage = tools.updates / generation
    stage.mkdir(parents=True)
    versions = {}
    with http_session() as session:
        for repo, asset_name, filename in (("yt-dlp/yt-dlp", "yt-dlp.exe", "yt-dlp.exe"),
                                           ("quickjs-ng/quickjs", "qjs-windows-x86_64.exe", "qjs.exe")):
            if cancelled and cancelled.is_set():
                raise Paused()
            report("Checking YouTube support…" if repo.startswith("yt-dlp") else "Checking JavaScript support…")
            response = session.get(f"https://api.github.com/repos/{repo}/releases/latest", timeout=(10, 30))
            response.raise_for_status()
            release = response.json()
            asset = next(a for a in release["assets"] if a["name"] == asset_name)
            digest = (asset.get("digest") or "").removeprefix("sha256:")
            if repo.startswith("yt-dlp"):
                sums = next(a for a in release["assets"] if a["name"] == "SHA2-256SUMS")
                response = session.get(sums["browser_download_url"], timeout=(10, 30))
                response.raise_for_status()
                digest = next(line.split()[0] for line in response.text.splitlines() if line.split()[-1].lstrip("*") == asset_name)
            if len(digest) != 64:
                raise UserError("The update could not be verified. Your current YouTube support is unchanged.")
            report("Downloading YouTube support…" if repo.startswith("yt-dlp") else "Downloading JavaScript support…")
            out = stage / filename
            h = hashlib.sha256()
            with session.get(asset["browser_download_url"], stream=True, timeout=(10, 30)) as response:
                response.raise_for_status()
                with out.open("xb") as stream:
                    for block in response.iter_content(256 * 1024):
                        if cancelled and cancelled.is_set():
                            raise Paused()
                        stream.write(block)
                        h.update(block)
            if h.hexdigest() != digest:
                raise UserError("The update was incomplete. Your current YouTube support is unchanged.")
            args = [str(out), "--version"] if filename == "yt-dlp.exe" else [str(out), "-e", "console.log('VedaBoat')"]
            code, output = run_process(args, timeout=60, cancelled=cancelled)
            if code:
                raise UserError("The updated tool could not start. Your current YouTube support is unchanged.")
            versions[filename] = {"version": release["tag_name"], "sha256": digest, "url": asset["browser_download_url"]}
    atomic_json(stage / "versions.json", versions)
    if cancelled and cancelled.is_set():
        raise Paused()
    atomic_json(tools.updates / "current.json", {"generation": generation})
    return "YouTube support is up to date (" + versions["yt-dlp.exe"]["version"] + ")."
