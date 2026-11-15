from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

from .model import Entry
from . import APP_NAME


def data_directory() -> Path:
    # The product rename must not split existing profiles, queues or tool updates.
    override = os.environ.get("VEDABOAT_DATA_DIR")
    return Path(override) if override else Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VedaBoat"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class State:
    """Versioned, transactional state outside the replaceable app directory."""

    def __init__(self, directory: Path | None = None):
        self.directory = directory or data_directory()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.directory / "vedaboat.sqlite3", check_same_thread=False, timeout=30)
        self.db.row_factory = sqlite3.Row
        if self.db.execute("PRAGMA user_version").fetchone()[0] > 3:
            self.db.close()
            raise RuntimeError(f"This saved state belongs to a newer {APP_NAME} version. Open the newer app to resume.")
        with self.db:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS files (
                    media_id TEXT NOT NULL, path TEXT NOT NULL, bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL, mtime_ns INTEGER NOT NULL,
                    PRIMARY KEY(media_id, path));
                CREATE TABLE IF NOT EXISTS paths (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS queue (
                    position INTEGER PRIMARY KEY, entry TEXT NOT NULL, destination TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending', error TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS run_files (
                    artifact TEXT NOT NULL, destination TEXT NOT NULL, path TEXT NOT NULL,
                    PRIMARY KEY(artifact, destination));
                PRAGMA user_version=3;
            """)
            self.db.execute("UPDATE queue SET status='pending' WHERE status IN ('downloading','converting','waiting_conversion','paused')")

    def get(self, key: str, default=None):
        with self.lock:
            row = self.db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key: str, value):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value, ensure_ascii=False)))

    def fixed_path(self, key: str, proposed: str) -> str:
        with self.lock, self.db:
            self.db.execute("INSERT OR IGNORE INTO paths VALUES (?,?)", (key, proposed))
            return self.db.execute("SELECT value FROM paths WHERE key=?", (key,)).fetchone()[0]

    def set_path(self, key: str, value: str):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO paths VALUES (?,?)", (key, value))

    def folder_path(self, identity: str, proposed: str) -> str:
        """Assign readable folders; disambiguate unrelated identically named owners."""
        key = "v21:folder:" + identity
        with self.lock, self.db:
            row = self.db.execute("SELECT value FROM paths WHERE key=?", (key,)).fetchone()
            if row:
                return row[0]
            used = {r[0].casefold() for r in self.db.execute("SELECT value FROM paths WHERE key LIKE 'v21:folder:%'")}
            candidate = proposed
            if candidate.casefold() in used:
                candidate += " [" + hashlib.sha256(identity.encode()).hexdigest()[:8] + "]"
            self.db.execute("INSERT INTO paths VALUES (?,?)", (key, candidate))
            return candidate

    def remember_file(self, media_id: str, path: Path):
        path = path.resolve()
        digest = sha256_file(path)
        stat = path.stat()
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?,?)", (media_id, str(path), stat.st_size, digest, stat.st_mtime_ns))

    def verified_file(self, media_id: str, root: Path | None = None, preferred: Path | None = None) -> Path | None:
        with self.lock:
            rows = self.db.execute("SELECT * FROM files WHERE media_id=?", (media_id,)).fetchall()
        if preferred is not None:
            expected=str(preferred.resolve()).casefold()
            rows.sort(key=lambda row:str(Path(row['path']).resolve()).casefold()!=expected)
        for row in rows:
            path = Path(row["path"])
            try:
                if root is not None and not path.resolve().is_relative_to(root.resolve()):
                    continue
                if path.stat().st_size == row["bytes"] and sha256_file(path) == row["sha256"]:
                    return path
            except OSError:
                pass
        return None

    def known_path(self, path: Path) -> bool:
        with self.lock:
            return self.db.execute("SELECT 1 FROM files WHERE path=?", (str(path.resolve()),)).fetchone() is not None

    def make_queue(self, entries: list[Entry], destination: Path, *, concurrency=None, repeat=None):
        with self.lock, self.db:
            if self.db.execute("SELECT 1 FROM queue WHERE status IN ('pending','downloading','converting','waiting_conversion')").fetchone():
                raise RuntimeError("Resume the unfinished downloads first.")
            self.db.execute("DELETE FROM queue")
            self.db.execute("DELETE FROM run_files")
            self.db.executemany("INSERT INTO queue(position,entry,destination) VALUES (?,?,?)", [
                (i, json.dumps(e.to_dict(), ensure_ascii=False), str(destination.resolve())) for i, e in enumerate(entries)
            ])
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('queue_started',?)", (json.dumps(time.time()),))
            options = {"concurrency": max(1, min(10, int(concurrency if concurrency is not None else self.get('concurrency', 1)))),
                       "repeat": bool(repeat if repeat is not None else self.get('repeat_downloads', False))}
            self.db.execute("INSERT OR REPLACE INTO settings VALUES ('queue_options',?)", (json.dumps(options),))

    def remember_run_file(self, artifact: str, destination: Path, path: Path):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO run_files VALUES (?,?,?)", (artifact, str(destination.resolve()), str(path.resolve())))

    def verified_run_file(self, artifact: str, destination: Path):
        with self.lock:
            row = self.db.execute("SELECT f.* FROM files f JOIN run_files r ON f.path=r.path AND f.media_id=r.artifact WHERE r.artifact=? AND r.destination=?",
                                  (artifact, str(destination.resolve()))).fetchone()
        if row:
            path = Path(row['path'])
            try:
                if path.stat().st_size == row['bytes'] and sha256_file(path) == row['sha256']:
                    return path
            except OSError:
                pass
        return None

    def queue(self) -> list[dict]:
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM queue ORDER BY position")]

    def job_status(self, position: int, status: str, error: str = ""):
        with self.lock, self.db:
            self.db.execute("UPDATE queue SET status=?,error=? WHERE position=?", (status, error, position))

    def retry_failed(self):
        with self.lock, self.db:
            self.db.execute("UPDATE queue SET status='pending',error='' WHERE status='failed'")

    def close(self):
        with self.lock:
            self.db.close()
