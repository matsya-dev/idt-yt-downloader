import hashlib
import json
from pathlib import Path

import pytest

import vedaboat.updater as updater
from vedaboat.model import UserError
from vedaboat.tools import Tools


class Response:
    def __init__(self, *, data=None, content=b"", text=""):
        self.data, self.content, self.text = data, content, text

    def json(self):
        return self.data

    def raise_for_status(self):
        pass

    def iter_content(self, _):
        yield self.content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class Session:
    def __init__(self, corrupt=False):
        self.corrupt = corrupt

    def get(self, url, **kw):
        yt = b"YOUTUBE TOOL"
        qjs = b"JS TOOL"
        if url.endswith("yt-dlp/yt-dlp/releases/latest"):
            return Response(data={"tag_name": "new", "assets": [
                {"name": "yt-dlp.exe", "browser_download_url": "https://example/yt.exe"},
                {"name": "SHA2-256SUMS", "browser_download_url": "https://example/sums"}]})
        if url.endswith("quickjs-ng/quickjs/releases/latest"):
            return Response(data={"tag_name": "new", "assets": [{"name": "qjs-windows-x86_64.exe", "browser_download_url": "https://example/qjs.exe", "digest": "sha256:" + hashlib.sha256(qjs).hexdigest()}]})
        if url.endswith("sums"):
            return Response(text=hashlib.sha256(yt).hexdigest() + "  yt-dlp.exe")
        if url.endswith("/yt.exe"):
            return Response(content=yt)
        return Response(content=b"CORRUPT" if self.corrupt else qjs)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def test_update_pair_is_published_together_and_resolved(monkeypatch, tmp_path):
    tools = Tools(tmp_path / "state", tmp_path / "bundled")
    monkeypatch.setattr(updater, "http_session", lambda: Session())
    monkeypatch.setattr(updater, "run_process", lambda *_args, **_kw: (0, "OK"))
    updater.update_youtube(tools)
    yt, js = tools.path("yt-dlp"), tools.path("qjs")
    assert yt.parent == js.parent
    assert yt.read_bytes() == b"YOUTUBE TOOL"
    assert js.read_bytes() == b"JS TOOL"


def test_failed_pair_keeps_previous_generation(monkeypatch, tmp_path):
    tools = Tools(tmp_path / "state", tmp_path / "bundled")
    old = tools.updates / "previous"
    old.mkdir(parents=True)
    (old / "yt-dlp.exe").write_bytes(b"OLD")
    (tools.updates / "current.json").write_text(json.dumps({"generation": "previous"}))
    monkeypatch.setattr(updater, "http_session", lambda: Session(corrupt=True))
    monkeypatch.setattr(updater, "run_process", lambda *_args, **_kw: (0, "OK"))
    with pytest.raises(UserError):
        updater.update_youtube(tools)
    assert tools.path("yt-dlp").parent == old


def test_corrupt_update_pointer_falls_back_to_bundled_tools(tmp_path):
    tools = Tools(tmp_path / "state", tmp_path / "bundled")
    tools.bundled.mkdir()
    (tools.bundled / "yt-dlp.exe").write_bytes(b"bundled")
    tools.updates.mkdir(parents=True)
    (tools.updates / "current.json").write_text(json.dumps({"generation": ["bad"]}))
    assert tools.path("yt-dlp") == tools.bundled / "yt-dlp.exe"
