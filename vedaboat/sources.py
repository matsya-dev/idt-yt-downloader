from __future__ import annotations

import json
import posixpath
import re
import threading
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .model import Collection, Entry, Paused, TREE_HOME, TREE_HOST, UserError, tree_media_url, tree_path, tree_url, youtube_url
from .tools import Tools, run_process
from . import ARCHIVE_NAME, __version__


def http_session(retry_count=3) -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = f"{ARCHIVE_NAME}/{__version__} (manual audio downloader)"
    retries = Retry(total=retry_count, backoff_factor=.6, status_forcelist=[429, 500, 502, 503, 504],
                    allowed_methods=["GET", "HEAD"], respect_retry_after_header=False)
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    return session


def decode_html(response: requests.Response) -> str:
    # Some older Andromeda pages declare Latin-1 while their names are UTF-8.
    try:
        return response.content.decode("utf-8")
    except UnicodeDecodeError:
        return response.content.decode(response.encoding or "windows-1252", errors="replace")


def remote_info(session: requests.Session, url: str, cancelled=None, timeout=(8, 12)) -> tuple[int | None, str]:
    size, validator = None, ""
    try:
        if cancelled and cancelled.is_set():
            raise Paused()
        with session.head(url, headers={"Accept-Encoding": "identity"}, timeout=timeout, allow_redirects=True) as response:
            if response.status_code == 200:
                size = int(response.headers["Content-Length"]) if response.headers.get("Content-Length", "").isdigit() else None
                validator = response.headers.get("ETag") or response.headers.get("Last-Modified", "")
        if size is None:
            if cancelled and cancelled.is_set():
                raise Paused()
            # The live site omits Content-Length on HEAD. A one-byte Range
            # request reveals the exact total without fetching the recording.
            with session.get(url, headers={"Range": "bytes=0-0", "Accept-Encoding": "identity"}, stream=True, timeout=timeout) as response:
                match = re.fullmatch(r"bytes 0-0/(\d+)", response.headers.get("Content-Range", ""))
                if response.status_code == 206 and match:
                    size = int(match[1])
                elif response.status_code == 200 and response.headers.get("Content-Length", "").isdigit():
                    size = int(response.headers["Content-Length"])
                validator = response.headers.get("ETag") or response.headers.get("Last-Modified") or validator
    except requests.RequestException:
        pass
    if cancelled and cancelled.is_set():
        raise Paused()
    return size, validator


class DesireTree:
    def parse(self, html: str, path: str) -> Collection:
        soup = BeautifulSoup(html, "html.parser")
        if "file not found" in (soup.title.get_text().lower() if soup.title else ""):
            raise UserError("This Desire Tree folder no longer exists. Try its parent folder.")
        entries: dict[str, Entry] = {}
        # Folder hrefs repeat in icons, names, counts and breadcrumbs. Only direct
        # children belong in the current collection, regardless of link order.
        for link in soup.find_all("a", href=True):
            raw_url = urljoin(TREE_HOME, link["href"])
            u = urlsplit(raw_url)
            if u.hostname != TREE_HOST:
                continue
            query = parse_qs(u.query)
            title = link.get_text(" ", strip=True).replace("\xa0", " ")
            if query.get("q") == ["f"] and "f" in query:
                child = tree_path(query["f"][0])
                if child == path or posixpath.dirname(child) != path:
                    continue
                if not title or re.fullmatch(r"[\d,]+ (?:folders?|files?)", title):
                    continue
                entries.setdefault(child, Entry("tree:" + child, "tree", "folder", title, tree_url(child), path=child))
            else:
                # Actual media lives at /<original hierarchy>/<original filename>.
                child = tree_path(unquote(u.path))
                if not child.lower().endswith(".mp3") or posixpath.dirname(child) != path:
                    continue
                entries[child] = Entry("tree:" + child, "tree", "audio", posixpath.basename(child),
                                       tree_media_url(child), path=child)
        # Andromeda file links may use the download route index.php?q=d&f=...
        for link in soup.find_all("a", href=True):
            u = urlsplit(urljoin(TREE_HOME, link["href"]))
            query = parse_qs(u.query)
            if u.hostname == TREE_HOST and query.get("q", [""])[0] in ("d", "a") and "f" in query:
                child = tree_path(query["f"][0])
                if child.lower().endswith(".mp3") and posixpath.dirname(child) == path:
                    entries[child] = Entry("tree:" + child, "tree", "audio", posixpath.basename(child), tree_media_url(child), path=child)
        title = path.rsplit("/", 1)[-1].replace("_", " ") if path != "/" else "All Desire Tree audio"
        parent = tree_url(posixpath.dirname(path) or "/") if path != "/" else ""
        moved = {'/04_-_ISKCON_Matajis': 'ISKCON Matajis', '/05_-_ISKCON_Chowpatty': 'ISKCON Chowpatty'}
        if path == '/':
            entries = {p: e for p, e in entries.items() if p not in moved}
        elif path == '/06_-_More':
            for p, name in moved.items():
                entries[p] = Entry('tree:' + p, 'tree', 'folder', name, tree_url(p), path=p)
        elif path in moved:
            parent = tree_url('/06_-_More')
        return Collection(tree_url(path), title, sorted(entries.values(), key=lambda e: (not e.container, e.title.casefold())), "tree", parent)

    def browse(self, url: str, cancelled: threading.Event | None = None) -> Collection:
        path = tree_path(url)
        if path.lower().endswith(".mp3"):
            e = Entry("tree:" + path, "tree", "audio", posixpath.basename(path), tree_media_url(path), path=path)
            return Collection(tree_media_url(path), e.title, [e], "tree", tree_url(posixpath.dirname(path)))
        if cancelled and cancelled.is_set():
            raise Paused()
        with http_session() as session:
            response = session.get(tree_url(path), timeout=(8, 20))
            response.raise_for_status()
            return self.parse(decode_html(response), path)

    def size(self, entry: Entry) -> int | None:
        with http_session() as session:
            entry.size = remote_info(session, entry.url)[0]
        return entry.size


def youtube_message(output: str) -> str:
    lower = output.lower()
    if "sign in" in lower or "bot" in lower:
        return "YouTube is asking for sign-in or a network check. Try again later or on another network."
    if any(s in lower for s in ("private video", "video unavailable", "is unavailable", "not available", "removed", "members-only", "copyright", "age-restricted")):
        return "This recording is unavailable or restricted on YouTube. Other recordings will continue."
    if any(s in lower for s in ("403", "signature", "challenge", "javascript")):
        return "YouTube support needs attention. Use Settings → Update YouTube support, then retry."
    if "not found" in lower or "404" in lower:
        return "This YouTube collection could not be found. Check the link."
    return "YouTube could not finish this request. Check your connection or update YouTube support in Settings."


class YouTube:
    def __init__(self, tools: Tools):
        self.tools = tools
        self.last_details = ""

    def browse(self, url: str, mode: str = "videos", cancelled: threading.Event | None = None) -> Collection:
        url, kind = youtube_url(url, mode)
        args = self.tools.yt_args() + ["--flat-playlist", "--dump-single-json", "--skip-download", "--ignore-errors", "--", url]
        code, output = run_process(args, cancelled=cancelled, timeout=1200)
        self.last_details = output[-20000:]
        if kind == "channel" and f"does not have a {mode} tab" in output:
            return Collection(url, "Channel playlists" if mode == "playlists" else "Channel videos", [], "youtube",
                              notice="This channel has no public playlists." if mode == "playlists" else "This channel has no public videos.")
        # Warnings may precede the one JSON result on the combined output stream.
        info = None
        for line in reversed(output.splitlines()):
            if line.startswith("{"):
                try:
                    info = json.loads(line)
                    break
                except ValueError:
                    pass
        if not info:
            raise UserError(youtube_message(output))
        return self.parse(info, url, kind, mode, code != 0)

    def parse(self, info: dict, url: str, kind: str, mode: str = "videos", incomplete=False) -> Collection:
        entries = []
        channel_id = info.get("channel_id") or (info.get("id") if kind == "channel" else "") or ""
        channel_title = info.get("channel") or info.get("uploader") or "Channel"
        collection_id = info.get("id", "") if kind == "playlist" else ""
        collection_title = info.get("title") or "Playlist"
        source_entries = info.get("entries", []) if "entries" in info else [info]
        seen = set()
        for i, item in enumerate(source_entries, 1):
            if not item:
                incomplete = True
                continue
            media_id = item.get("id", "")
            is_playlist = kind == "channel" and mode == "playlists"
            if is_playlist:
                playlist_url = item.get("webpage_url") or item.get("url") or f"https://www.youtube.com/playlist?list={media_id}"
                try:
                    playlist_url, pkind = youtube_url(playlist_url)
                    if pkind != "playlist":
                        continue
                except UserError:
                    continue
                entry = Entry("playlist:" + media_id, "youtube", "playlist", item.get("title") or media_id,
                              playlist_url, collection_id=media_id, channel_id=channel_id, channel_title=channel_title)
            else:
                if not re.fullmatch(r"[\w-]{11}", media_id, re.ASCII):
                    incomplete = True
                    continue
                key = "youtube:" + media_id + ("@" + collection_id if collection_id else "")
                title = item.get("title") or media_id
                availability = item.get("availability")
                available = availability not in ("private", "premium_only", "subscriber_only", "needs_auth", "unavailable") and title not in ("[Private video]", "[Deleted video]")
                entry = Entry(key, "youtube", "video", title, f"https://www.youtube.com/watch?v={media_id}",
                              video_id=media_id, collection_id=collection_id, collection_title=collection_title if collection_id else "",
                              channel_id=channel_id or item.get("channel_id") or "", channel_title=(channel_title if channel_title != "Channel" else item.get("channel") or item.get("uploader") or "Unknown channel"),
                              index=int(item.get("playlist_index") or i) if collection_id else 0,
                              duration=item.get("duration"), available=available)
            if entry.key not in seen:
                seen.add(entry.key)
                entries.append(entry)
        if kind == "channel" and mode == "playlists":
            entries.sort(key=lambda e: e.title.casefold())
        title = info.get("title") or info.get("channel") or "YouTube recording"
        notice = "Some entries could not be listed. Refresh to try again; unavailable recordings are reported when downloading." if incomplete else ""
        return Collection(url, title, entries, "youtube", notice=notice)
