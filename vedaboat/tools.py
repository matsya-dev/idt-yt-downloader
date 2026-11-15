from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

from .model import Paused, UserError, audio_quality
from . import APP_NAME

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def application_directory() -> Path:
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent


def stop_process(process: subprocess.Popen):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, creationflags=NO_WINDOW, timeout=10)
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def run_process(args: list[str], *, cancelled: threading.Event | None = None,
                on_line: Callable[[str], None] | None = None, timeout: float = 900,
                cwd: Path | None = None) -> tuple[int, str]:
    """Drain output off-thread so a silent tool can still be paused promptly."""
    process = subprocess.Popen([str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace",
                               creationflags=NO_WINDOW, cwd=cwd)
    output: queue.Queue = queue.Queue()

    def read():
        try:
            for line in process.stdout:
                output.put(line.rstrip("\r\n"))
        finally:
            output.put(None)

    threading.Thread(target=read, daemon=True).start()
    started = time.monotonic()
    lines = []
    try:
        while True:
            if cancelled and cancelled.is_set():
                raise Paused()
            if time.monotonic() - started > timeout:
                raise UserError("The service took too long to respond. Try again later.")
            try:
                line = output.get(timeout=.1)
            except queue.Empty:
                continue
            if line is None:
                break
            lines.append(line)
            if on_line:
                on_line(line)
        return process.wait(timeout=10), "\n".join(lines)
    finally:
        if process.poll() is None:
            stop_process(process)
        process.stdout.close()


class Tools:
    def __init__(self, data_dir: Path, bundled: Path | None = None):
        self.bundled = bundled or application_directory() / "tools"
        self.updates = data_dir / "tools"

    def path(self, name: str) -> Path:
        name += ".exe" if os.name == "nt" else ""
        generation = ""
        try:
            generation = json.loads((self.updates / "current.json").read_text(encoding="utf-8"))["generation"]
            if not isinstance(generation, str) or not generation.replace("-", "").isalnum():
                generation = ""
        except (OSError, ValueError, KeyError):
            pass
        updated = self.updates / generation / name if generation else self.updates / name
        # Updater publishes tools using atomic rename only after successful checks.
        path = updated if updated.exists() else self.bundled / name
        if not path.is_file():
            raise UserError(f"A bundled tool is missing. Unzip the complete {APP_NAME} package again.")
        return path

    def yt_args(self) -> list[str]:
        return [str(self.path("yt-dlp")), "--ignore-config", "--no-plugin-dirs", "--encoding", "utf-8",
                "--no-colors", "--socket-timeout", "12", "--retries", "3", "--fragment-retries", "3",
                "--extractor-retries", "2", "--no-js-runtimes", "--js-runtimes", f"quickjs:{self.path('qjs')}"]

    def probe(self, path: Path) -> dict:
        code, output = run_process([str(self.path("ffprobe")), "-v", "error", "-select_streams", "a:0",
                                    "-show_entries", "stream=codec_name,bit_rate:format=duration", "-of", "json", str(path)], timeout=45)
        try:
            info = json.loads(output)
            if code or not info.get("streams") or float(info.get("format", {}).get("duration", 0)) <= 0:
                raise ValueError()
            return info
        except (ValueError, TypeError):
            raise UserError("The audio file is incomplete or cannot be read. Retry this recording.")

    def convert(self, source: Path, target: Path, duration: float | None = None, quality: int = 128):
        target.parent.mkdir(parents=True, exist_ok=True)
        quality=audio_quality(quality)
        rate=["-ar","44100"] if quality>=192 else []
        code, output = run_process([str(self.path("ffmpeg")), "-hide_banner", "-nostdin", "-v", "error", "-n",
                                    "-i", str(source), "-vn", "-map", "0:a:0", "-c:a", "libmp3lame", "-b:a", f"{quality}k",*rate,
                                    "-f", "mp3", str(target)], timeout=max(300, (duration or 0) * 2))
        if code:
            raise UserError("MP3 conversion failed. The downloaded audio is saved; Retry failed will try conversion again.")
        info = self.probe(target)
        if info["streams"][0]["codec_name"] != "mp3":
            raise UserError("MP3 conversion could not be verified. The downloaded audio has been kept.")
        if int(info["streams"][0].get("bit_rate",0)) != quality*1000:
            raise UserError("The requested MP3 quality could not be verified. The downloaded audio has been kept for retry.")
