from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path
from typing import Callable

import requests

from .model import Entry, Paused, UserError, audio_quality, confined, devotee_layout, format_size, safe_component, tree_relative
from .sources import http_session, remote_info, youtube_message
from .state import State
from .tools import Tools, run_process
from . import APP_NAME

RESERVE = 32 * 1024 * 1024


def check_space(path: Path, needed: int):
    ancestor = path
    while not ancestor.exists() and ancestor != ancestor.parent:
        ancestor = ancestor.parent
    if shutil.disk_usage(ancestor).free < needed + RESERVE:
        raise UserError(f"There is not enough free space. Free at least {format_size(needed + RESERVE)} and resume.")


def atomic_json(path: Path, data: dict):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def publish_file(source: Path, target: Path):
    """Publish without replacing any existing filename (on all platforms)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, target)
    except FileExistsError:
        raise
    except OSError:
        # Exclusive creation is also safe on FAT/exFAT, where hard links do not work.
        try:
            with source.open("rb") as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
                dst.flush()
                os.fsync(dst.fileno())
        except FileExistsError:
            raise
        except BaseException:
            if target.exists():
                target.unlink()
            raise


class Engine:
    """Bounded network workers, serialized conversion, persistent per-run reuse."""

    def __init__(self, state: State, tools: Tools, notify: Callable[[str, dict], None] | None = None):
        self.state = state
        self.tools = tools
        self.notify = notify or (lambda *_: None)
        self.pause = threading.Event()
        self.thread: threading.Thread | None = None
        self.converting = False
        self.details: list[str] = []
        self.last_progress = 0.0
        self.conversion_lock = threading.Lock()
        self.media_locks = {}
        self.guard = threading.RLock()
        self.local = threading.local()
        self.options = self.state.get('queue_options', {'concurrency': 1, 'repeat': False})

    @property
    def running(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def start(self):
        if self.running:
            return
        self.pause.clear()
        self.thread = threading.Thread(target=self.run, daemon=True, name="VedaBoat-downloads")
        self.thread.start()

    def request_pause(self):
        self.pause.set()
        self.notify("pausing", {"converting": self.converting})

    def report_progress(self, received: int, total: int | None):
        now = time.monotonic()
        if now - self.last_progress >= .15 or total and received >= total:
            self.last_progress = now
            self.notify("progress", {"bytes": received, "total": total, "position": getattr(self.local, 'position', 0)})

    def log(self, text: str):
        self.details.append(text)
        self.details = self.details[-300:]
        try:
            with (self.state.directory / "details.log").open("a", encoding="utf-8") as stream:
                stream.write(time.strftime("%Y-%m-%d %H:%M:%S ") + text + "\n")
            log = self.state.directory / "details.log"
            if log.stat().st_size > 2 * 1024 * 1024:
                text_tail = log.read_text(encoding="utf-8", errors="replace")[-1024 * 1024:]
                log.write_text(text_tail, encoding="utf-8")
        except OSError:
            pass

    def run(self):
        self.options = self.state.get('queue_options', {'concurrency': 1, 'repeat': False})
        try:
            rows = iter(r for r in self.state.queue() if r['status'] == 'pending')
            limit = max(1, min(10, int(self.options.get('concurrency', 1))))
            with ThreadPoolExecutor(max_workers=limit, thread_name_prefix='VedaBoat-transfer') as pool:
                active = set()
                exhausted = False
                while active or not exhausted:
                    while not self.pause.is_set() and not exhausted and len(active) < limit:
                        row = next(rows, None)
                        if row is None:
                            exhausted = True
                        else:
                            active.add(pool.submit(self.run_job, row))
                    if not active:
                        break
                    finished, active = wait(active, timeout=.1, return_when=FIRST_COMPLETED)
                    for future in finished:
                        future.result()
        except Exception as error:
            self.log(f"Queue: {type(error).__name__}: {error}")
            self.notify("error", {"message": f"Downloads stopped. Your progress is saved; reopen {APP_NAME} to resume."})
        finally:
            self.converting = False
            self.notify("stopped", {})

    def run_job(self, row):
        entry = Entry.from_dict(json.loads(row["entry"]))
        destination = Path(row["destination"])
        position = row["position"]
        self.local.position = position
        # Shared video occurrences must not race over source/partial files.
        with self.guard:
            lock = self.media_locks.setdefault((str(destination.resolve()), entry.media_id), threading.Lock())
        try:
            while not lock.acquire(timeout=.1):
                if self.pause.is_set():
                    raise Paused()
            try:
                if self.pause.is_set():
                    raise Paused()
                self.process_job(entry, destination, position)
            finally:
                lock.release()
        except Paused:
            self.state.job_status(position, "pending")
        except Exception as error:
            self.log(f"{entry.media_id}: {type(error).__name__}: {error}")
            message = str(error) if isinstance(error, UserError) else "This recording could not be saved. Check the connection and download folder, then retry."
            self.state.job_status(position, "failed", message)
            self.notify("failed", {"title": entry.title, "message": message})
            if isinstance(error, OSError) and getattr(error, "errno", None) == 28 or "not enough free space" in str(error):
                self.pause.set()

    def process_job(self, entry, destination, position):
        self.state.job_status(position, "downloading")
        self.last_progress = 0.0
        self.notify("current", {"title": entry.title, "position": position})
        if not entry.available:
            raise UserError("This recording is unavailable or restricted on YouTube.")
        destination.mkdir(parents=True, exist_ok=True)
        if entry.source == "tree":
            skipped = self.download_tree(entry, destination)
        else:
            skipped = self.download_youtube(entry, destination, position)
        path = self.target_path(entry, destination)
        if path.is_file():
            self.state.remember_run_file(entry.artifact_id, destination, path)
        self.state.job_status(position, "skipped" if skipped else "done")
        self.notify("completed", {"title": entry.title, "skipped": skipped})

    def relative_path(self, entry: Entry) -> Path:
        if entry.layout_version >= 2:
            if entry.source == "tree":
                owner, name, tail = devotee_layout(entry.path)
                folder = self.state.folder_path("tree:" + owner, str(Path("Desire Tree Downloads") / name))
                return Path(folder) / tail
            owner = entry.channel_id or "title:" + (entry.channel_title or "Unknown channel")
            channel = self.state.folder_path("youtube:" + owner,
                str(Path("YouTube downloads") / safe_component(entry.channel_title or "Unknown channel", 100)))
            folder = Path(channel)
            if entry.collection_id:
                folder = Path(self.state.folder_path("playlist:" + entry.collection_id,
                    str(folder / safe_component(entry.collection_title or "Playlist", 100))))
            quality = audio_quality(entry.quality)
            tag = f" [{quality}kbps]" if quality != 128 else ""
            name = safe_component(entry.title, 100) + f" [{entry.video_id}]" + tag + ".mp3"
            return folder / ((f"{entry.index:04d} - " if entry.collection_id else "") + name)
        if entry.source == "tree":
            return tree_relative(entry.path)
        name = safe_component(entry.title, 100) + f" [{entry.video_id}].mp3"
        if entry.collection_id:
            channel = safe_component(entry.channel_title or "Channel", 55) + (f" [{entry.channel_id}]" if entry.channel_id else "")
            proposed = str(Path("YouTube") / channel / (safe_component(entry.collection_title, 65) + f" [{entry.collection_id}]"))
            folder = self.state.fixed_path("playlist:" + entry.collection_id, proposed)
            return Path(folder) / (f"{entry.index:04d} - " + name)
        return Path("YouTube") / "Videos" / name

    def target_path(self, entry: Entry, destination: Path) -> Path:
        key = self.path_key(entry, destination)
        relative = Path(self.state.fixed_path(key, str(self.relative_path(entry))))
        path = confined(destination, relative)
        return path

    def path_key(self, entry: Entry, destination: Path) -> str:
        base = str(destination.resolve()) + "|" + entry.key
        return "v21|" + base + f"|{audio_quality(entry.quality)}" if entry.layout_version >= 2 else base

    def vacant_target(self, entry: Entry, destination: Path, path: Path) -> Path:
        key = self.path_key(entry, destination)
        original = confined(destination,Path(self.state.fixed_path('original:'+key,str(path.relative_to(destination.resolve())))))
        serial = 2
        while path.exists():
            path = original.with_name(original.stem + f" ({serial})" + original.suffix)
            serial += 1
        self.state.set_path(key, str(path.relative_to(destination.resolve())))
        return path

    def existing(self, entry: Entry, destination: Path, target: Path) -> bool:
        verified = (self.state.verified_run_file(entry.artifact_id, destination) if self.options.get('repeat')
                    else self.state.verified_file(entry.artifact_id, destination, preferred=target))
        if verified:
            if target.resolve() == verified.resolve():
                return True
            target = self.vacant_target(entry, destination, target)
            check_space(destination, verified.stat().st_size)
            publish_file(verified, target)
            self.state.remember_file(entry.artifact_id, target)
            return True
        return False

    def download_tree(self, entry: Entry, destination: Path) -> bool:
        target = self.target_path(entry, destination)
        if self.existing(entry, destination, target):
            return True
        work = destination / ".vedaboat" / "partials"
        work.mkdir(parents=True, exist_ok=True)
        token = hashlib.sha256(entry.media_id.encode()).hexdigest()
        part = work / (token + ".mp3.part")
        meta_path = work / (token + ".json")
        # Queue retries are explicit and interruptible; do not bury retry waits
        # inside urllib3 while the user is trying to pause a stalled connection.
        with http_session(retry_count=0) as session:
            size, validator = remote_info(session, entry.url, self.pause, (4, 3))
            candidates=[target]
            if entry.layout_version>=2:
                legacy=confined(destination,tree_relative(entry.path))
                if legacy!=target:
                    candidates.append(legacy)
            for candidate in ([] if self.options.get('repeat') else candidates):
                if candidate.exists() and size and not self.state.known_path(candidate) and candidate.stat().st_size==size:
                    try:
                        self.tools.probe(candidate)
                        self.state.remember_file(entry.media_id,candidate)
                        if candidate!=target:
                            target=self.vacant_target(entry,destination,target)
                            check_space(destination,size)
                            publish_file(candidate,target)
                            self.state.remember_file(entry.media_id,target)
                        return True
                    except UserError:
                        pass
            target = self.vacant_target(entry, destination, target)
            meta = {}
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            if part.exists() and (meta.get("url") != entry.url or (validator and meta.get("validator") != validator) or (size and meta.get("size") != size)):
                # Keep a superseded partial rather than attaching it to changed bytes.
                part.rename(part.with_name(part.name + f".old-{time.time_ns()}"))
            atomic_json(meta_path, {"url": entry.url, "validator": validator, "size": size})
            last_error = None
            for attempt in range(4):
                if self.pause.is_set():
                    raise Paused()
                offset = part.stat().st_size if part.exists() else 0
                # A complete partial from an interrupted finalization needs no network transfer.
                if size and offset == size:
                    break
                if size and offset > size:
                    part.rename(part.with_name(part.name + f".old-{time.time_ns()}"))
                    offset = 0
                check_space(destination, max(0, (size or 16 * 1024 * 1024) - offset))
                headers = {"Accept-Encoding": "identity"}
                if offset:
                    headers["Range"] = f"bytes={offset}-"
                    if validator:
                        headers["If-Range"] = validator
                try:
                    with session.get(entry.url, headers=headers, stream=True, timeout=(4, 3)) as response:
                        response.raise_for_status()
                        if offset and response.status_code == 206:
                            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                            if not match or int(match[1]) != offset or size and int(match[3]) != size:
                                raise UserError("The server returned an inconsistent partial file. Retry later.")
                            size = int(match[3])
                        else:
                            offset = 0
                            size = int(response.headers["Content-Length"]) if response.headers.get("Content-Length", "").isdigit() else size
                        content_type = response.headers.get("Content-Type", "").lower()
                        if "text/html" in content_type:
                            raise UserError("The website returned a page instead of this MP3. Try again later.")
                        validator = response.headers.get("ETag") or response.headers.get("Last-Modified") or validator
                        atomic_json(meta_path, {"url": entry.url, "validator": validator, "size": size})
                        received, last_space = offset, offset
                        with part.open("ab" if offset else "wb") as stream:
                            for chunk in response.iter_content(64 * 1024):
                                if self.pause.is_set():
                                    stream.flush()
                                    os.fsync(stream.fileno())
                                    raise Paused()
                                if not chunk:
                                    continue
                                stream.write(chunk)
                                received += len(chunk)
                                if received - last_space >= 8 * 1024 * 1024:
                                    check_space(destination, max(0, (size or received) - received))
                                    last_space = received
                                self.report_progress(received, size)
                            stream.flush()
                            os.fsync(stream.fileno())
                        if size is not None and received != size:
                            raise requests.ConnectionError("Incomplete Content-Length")
                        size = received
                        atomic_json(meta_path, {"url": entry.url, "validator": validator, "size": size})
                        break
                except (requests.RequestException, TimeoutError) as error:
                    last_error = error
                    if attempt == 3:
                        raise UserError("The connection was interrupted. Your partial MP3 is saved; Retry failed will resume it.") from error
                    if self.pause.wait(min(2 ** attempt, 4)):
                        raise Paused()
            if not part.exists() or not part.stat().st_size or size is not None and part.stat().st_size != size:
                raise UserError("This MP3 is incomplete. Retry failed will resume it.") from last_error
            try:
                self.tools.probe(part)
            except UserError:
                part.rename(part.with_name(part.name + f".unreadable-{time.time_ns()}"))
                raise
            target = self.vacant_target(entry, destination, target)
            publish_file(part, target)
            self.state.remember_file(entry.media_id, target)
            part.unlink()
            meta_path.unlink(missing_ok=True)
            return False

    def download_youtube(self, entry: Entry, destination: Path, position: int) -> bool:
        target = self.target_path(entry, destination)
        if self.existing(entry, destination, target):
            return True
        target = self.vacant_target(entry, destination, target)
        work = destination / ".vedaboat" / "youtube" / entry.video_id
        work.mkdir(parents=True, exist_ok=True)
        source_marker = work / "download.json"
        source = None
        try:
            cached = Path(json.loads(source_marker.read_text(encoding="utf-8"))["source"])
            if cached.is_file() and cached.resolve().parent == work.resolve():
                self.tools.probe(cached)
                source = cached
        except (OSError, ValueError, KeyError, UserError):
            pass
        if source is None:
            check_space(destination, max(24 * 1024 * 1024, int((entry.duration or 0) * 48000)))
            if self.pause.is_set():
                raise Paused()
            found = []

            def line_handler(line: str):
                if line.startswith("VBPROGRESS|"):
                    parts = line.split("|")
                    try:
                        self.report_progress(int(float(parts[1])), int(float(parts[2])) if parts[2] not in ("NA", "None") else None)
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("VBFILE|"):
                    found.append(line[7:])
                else:
                    self.log(line)

            args = self.tools.yt_args() + ["--no-playlist", "--no-overwrites", "--continue", "--newline",
                "--concurrent-fragments", "1", "--abort-on-unavailable-fragments", "--no-mtime",
                "--ffmpeg-location", str(self.tools.path("ffmpeg").parent),
                "-f", "bestaudio/best", "-o", str(work).replace("%", "%%") + "/audio.%(ext)s",
                "--progress-template", "download:VBPROGRESS|%(progress.downloaded_bytes)s|%(progress.total_bytes_estimate)s",
                "--print", "after_move:VBFILE|%(filepath)s", "--no-simulate", "--", entry.url]
            code, output = run_process(args, cancelled=self.pause, on_line=line_handler, timeout=24 * 3600)
            if code or not found:
                raise UserError(youtube_message(output))
            source = Path(found[-1])
            if source.resolve().parent != work.resolve() or not source.is_file():
                raise UserError("The downloaded audio could not be located. Its partial files are kept for retry.")
            self.tools.probe(source)
            atomic_json(source_marker, {"source": str(source.resolve())})
        if self.pause.is_set():
            raise Paused()
        check_space(destination, max(4 * 1024 * 1024, entry.estimated_size or 0))
        self.state.job_status(position, 'waiting_conversion')
        while not self.conversion_lock.acquire(timeout=.1):
            if self.pause.is_set():
                raise Paused()
        if self.pause.is_set():
            self.conversion_lock.release()
            raise Paused()
        self.converting = True
        converted = work / "converted.mp3"
        try:
            self.state.job_status(position, "converting")
            self.notify("converting", {"title": entry.title})
            # A previous failed conversion is never mistaken for completed output.
            converted.unlink(missing_ok=True)
            self.tools.convert(source, converted, entry.duration, audio_quality(entry.quality))
            target = self.vacant_target(entry, destination, target)
            publish_file(converted, target)
            self.state.remember_file(entry.artifact_id, target)
            converted.unlink(missing_ok=True)
            source.unlink(missing_ok=True)
            source_marker.unlink(missing_ok=True)
            return False
        finally:
            self.converting = False
            self.conversion_lock.release()
