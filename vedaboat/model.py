from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

TREE_HOST = "audio.iskcondesiretree.com"
TREE_HOME = f"https://{TREE_HOST}/index.php"
BVKS_PATH = "/02_-_ISKCON_Swamis/ISKCON_Swamis_-_A_to_C/His_Holiness_Bhakti_Vikas_Swami"
CHANNELS = (
    ("Bhakti Vikasa Swami", "https://www.youtube.com/@BhaktiVikasaSwami"),
    ("BVKS · English", "https://www.youtube.com/@BhaktiVikasaSwamiEnglish"),
    ("BVKS · Telugu", "https://www.youtube.com/@భక్తివికాసస్వామి"),
    ("BVKS · Bengali", "https://www.youtube.com/@ভক্তিবিকাশস্বামী"),
    ("BVKS · Tamil", "https://www.youtube.com/@BhaktiVikasaSwamiTamil"),
    ("Logica Spiritus", "https://www.youtube.com/@LogicaSpiritus"),
)
YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}
QUALITY_OPTIONS = (96, 128, 192, 256, 320)


def audio_quality(value) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 128
    return value if value in QUALITY_OPTIONS else 128


class UserError(Exception):
    """A concise explanation suitable for the main interface."""


class Paused(Exception):
    pass


def tree_path(value: str) -> str:
    """Decode a site URL once, rejecting traversal and foreign hosts."""
    value = value.strip()
    if "://" in value:
        u = urlsplit(value)
        if u.scheme not in ("http", "https") or u.hostname != TREE_HOST or u.username or u.port not in (None, 80, 443):
            raise UserError("Use a link from audio.iskcondesiretree.com.")
        if u.path.rstrip("/") in ("", "/index.php"):
            value = parse_qs(u.query).get("f", [""])[0]
        else:
            value = unquote(u.path)
    parts = value.replace("\\", "/").strip("/").split("/")
    if any(p in (".", "..") or "\x00" in p or ":" in p for p in parts):
        raise UserError("This link contains an invalid folder path.")
    return "/" + "/".join(p for p in parts if p) if any(parts) else "/"


def tree_url(path: str) -> str:
    return TREE_HOME if path == "/" else TREE_HOME + "?" + urlencode({"q": "f", "f": path})


def tree_media_url(path: str) -> str:
    return f"https://{TREE_HOST}" + quote(path, safe="/")


def youtube_url(value: str, mode: str = "videos") -> tuple[str, str]:
    """Return canonical public video/playlist/channel URL and collection kind."""
    try:
        u = urlsplit(value.strip())
        if u.scheme not in ("http", "https") or u.hostname not in YT_HOSTS or u.username or u.port not in (None, 80, 443):
            raise ValueError()
        query = parse_qs(u.query)
        path = unquote(u.path).rstrip("/")
        if "list" in query:
            pid = query["list"][0]
            if not re.fullmatch(r"[\w-]{2,100}", pid, re.ASCII):
                raise ValueError()
            return "https://www.youtube.com/playlist?" + urlencode({"list": pid}), "playlist"
        vid = None
        if u.hostname.endswith("youtu.be"):
            vid = path.lstrip("/")
        elif path == "/watch":
            vid = query.get("v", [""])[0]
        elif path.startswith(("/shorts/", "/live/", "/embed/")):
            vid = path.split("/")[2]
        if vid is not None:
            if not re.fullmatch(r"[\w-]{11}", vid, re.ASCII):
                raise ValueError()
            return f"https://www.youtube.com/watch?v={vid}", "video"
        segs = path.split("/")
        if len(segs) >= 2 and (segs[1].startswith("@") or segs[1] in ("channel", "c", "user")):
            count = 2 if segs[1].startswith("@") else 3
            if len(segs) < count or not segs[count - 1]:
                raise ValueError()
            channel = "/".join(segs[:count])
            return "https://www.youtube.com" + quote(channel, safe="/@") + "/" + mode, "channel"
    except (ValueError, IndexError):
        pass
    raise UserError("Paste a complete YouTube video, playlist, or channel link.")


def safe_component(text: str, limit: int = 96) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).rstrip(" .")
    if not cleaned:
        cleaned = "Untitled"
    if cleaned.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(10)), *(f"LPT{i}" for i in range(10))}:
        cleaned = "_" + cleaned
    if len(cleaned) > limit:
        cleaned = cleaned[:limit - 10].rstrip(" .") + "~" + hashlib.sha256(text.encode()).hexdigest()[:8]
    return cleaned


def tree_relative(path: str) -> Path:
    parts = tree_path(path).strip("/").split("/")
    # Original names are retained unless Windows cannot represent a component.
    # A hash prevents two invalid or too-long source names collapsing together.
    result = []
    for index, p in enumerate(parts):
        clean = safe_component(p, 180)
        if clean != p:
            suffix = safe_component(Path(p).suffix, 20) if index == len(parts) - 1 and Path(p).suffix else ""
            stem = p[:-len(Path(p).suffix)] if suffix else p
            clean = safe_component(stem, 150) + "~" + hashlib.sha256(p.encode()).hexdigest()[:8] + suffix
        result.append(clean)
    return Path(*result)


def devotee_layout(path: str) -> tuple[str, str, Path]:
    """Locate the named speaker root independently of the route used to browse."""
    parts = tree_path(path).strip("/").split("/")
    folders = parts[:-1]
    index = 0
    for i, name in enumerate(folders):
        if name.startswith(("His_Holiness_", "His_Grace_", "Her_Grace_", "His_Divine_Grace_")):
            index = i
            break
    else:
        if folders and re.match(r"\d+_-_", folders[0]):
            if "Srila_Prabhupada" in folders[0]:
                index = 0
            else:
                index = 1 if len(folders) > 1 else 0
                while index < len(folders) - 1 and re.search(r"ISKCON_(?:Swamis|Prabhujis|Matajis)_-_|(?:A|D|R)_to_", folders[index]):
                    index += 1
    if not folders:
        return "/", "Other recordings", tree_relative(path)
    ancestor = "/" + "/".join(parts[:index + 1])
    name = re.sub(r"^\d+_-_", "", parts[index])
    return ancestor, safe_component(name, 130), tree_relative("/" + "/".join(parts[index + 1:]))


def confined(root: Path, relative: Path) -> Path:
    root = root.resolve()
    result = (root / relative).resolve()
    if not result.is_relative_to(root) or result == root:
        raise UserError("The destination path is not inside the chosen folder.")
    return result


@dataclass
class Entry:
    key: str
    source: str
    kind: str
    title: str
    url: str
    path: str = ""
    video_id: str = ""
    collection_id: str = ""
    collection_title: str = ""
    channel_id: str = ""
    channel_title: str = ""
    index: int = 0
    duration: float | None = None
    size: int | None = None
    available: bool = True
    quality: int = 128
    layout_version: int = 2

    @property
    def container(self) -> bool:
        return self.kind in ("folder", "playlist")

    @property
    def media_id(self) -> str:
        return "tree:" + self.path if self.source == "tree" else "youtube:" + self.video_id

    @property
    def estimated_size(self) -> int | None:
        return self.size_for(self.quality)

    def size_for(self, quality=128) -> int | None:
        return self.size if self.source == "tree" else int(self.duration * audio_quality(quality) * 1000 / 8) if self.duration else None

    @property
    def artifact_id(self) -> str:
        return self.media_id if self.source == "tree" or audio_quality(self.quality) == 128 else self.media_id + f":mp3:{audio_quality(self.quality)}"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Entry:
        values = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        values.setdefault("layout_version", 1)  # Finish queues created by 2.0 in their original paths.
        values["quality"] = audio_quality(values.get("quality", 128))
        return cls(**values)


@dataclass
class Collection:
    url: str
    title: str
    entries: list[Entry]
    source: str
    parent_url: str = ""
    notice: str = ""


def format_size(size: int | None) -> str:
    if size is None:
        return "size unknown"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:,.1f} {unit}"
        size /= 1024
    return f"{size:,.1f} PB"
