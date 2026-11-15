from __future__ import annotations

import hashlib
import json
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import vedaboat.engine as engine_module
from vedaboat.engine import Engine, atomic_json
from vedaboat.model import Entry, Paused, UserError
from vedaboat.state import State, sha256_file
from vedaboat.tools import Tools, run_process


class ProbeStub:
    def probe(self, path):
        if not path.stat().st_size or path.read_bytes().startswith(b"<html>"):
            raise UserError("Invalid audio")
        return {"streams": [{"codec_name": "mp3"}], "format": {"duration": "2"}}


@pytest.fixture
def server():
    config = {"data": bytes(range(256)) * 8192, "ranges": True, "requests": [], "etag": '"v1"'}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_HEAD(self):
            self.send_response(200)
            self.send_header("Content-Length", len(config["data"]))
            self.send_header("ETag", config["etag"])
            self.end_headers()

        def do_GET(self):
            requested = self.headers.get("Range")
            config["requests"].append(requested)
            offset = int(requested[6:].split("-")[0]) if requested and config["ranges"] else 0
            self.send_response(206 if offset else 200)
            data = config["data"][offset:]
            self.send_header("Content-Length", len(data))
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("ETag", config["etag"])
            if offset:
                self.send_header("Content-Range", f"bytes {offset}-{len(config['data']) - 1}/{len(config['data'])}")
            self.end_headers()
            try:
                for i in range(0, len(data), 8192):
                    self.wfile.write(data[i:i + 8192])
                    if config.get("slow"):
                        time.sleep(.002)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    config["url"] = f"http://127.0.0.1:{http.server_port}/one.mp3"
    yield config
    http.shutdown()
    http.server_close()


def audio(url, path="/site/বাংলা/original.mp3"):
    return Entry("tree:" + path, "tree", "audio", Path(path).name, url, path=path)


def test_download_and_verified_skip_without_second_transfer(tmp_path, server):
    state = State(tmp_path / "state")
    engine = Engine(state, ProbeStub())
    e = audio(server["url"])
    root = tmp_path / "downloads"
    assert engine.download_tree(e, root) is False
    target = engine.target_path(e, root)
    assert target.read_bytes() == server["data"]
    assert engine.download_tree(e, root) is True
    assert len(server["requests"]) == 1
    state.close()


def test_pause_and_reopen_resume_exact_bytes(tmp_path, server):
    server["slow"] = True
    state = State(tmp_path / "state")
    entry, root = audio(server["url"]), tmp_path / "downloads"
    engine = Engine(state, ProbeStub())

    def progress(kind, data):
        if kind == "progress" and data["bytes"] >= 128 * 1024:
            engine.pause.set()

    engine.notify = progress
    with pytest.raises(Paused):
        engine.download_tree(entry, root)
    state.close()
    state = State(tmp_path / "state")
    resumed = Engine(state, ProbeStub())
    assert resumed.download_tree(entry, root) is False
    assert any(r and r.startswith("bytes=") for r in server["requests"])
    assert resumed.target_path(entry, root).read_bytes() == server["data"]
    state.close()


def test_range_ignored_restarts_instead_of_appending(tmp_path, server):
    state = State(tmp_path / "state")
    root, entry = tmp_path / "downloads", audio(server["url"])
    work = root / ".vedaboat" / "partials"
    work.mkdir(parents=True)
    token = hashlib.sha256(entry.media_id.encode()).hexdigest()
    (work / (token + ".mp3.part")).write_bytes(server["data"][:12345])
    atomic_json(work / (token + ".json"), {"url": entry.url, "size": len(server["data"]), "validator": server["etag"]})
    server["ranges"] = False
    engine = Engine(state, ProbeStub())
    engine.download_tree(entry, root)
    assert engine.target_path(entry, root).read_bytes() == server["data"]
    state.close()


def test_remote_changed_keeps_old_partial_and_restarts(tmp_path, server):
    state = State(tmp_path / "state")
    root, entry = tmp_path / "downloads", audio(server["url"])
    work = root / ".vedaboat" / "partials"
    work.mkdir(parents=True)
    token = hashlib.sha256(entry.media_id.encode()).hexdigest()
    (work / (token + ".mp3.part")).write_bytes(b"OLD DATA")
    atomic_json(work / (token + ".json"), {"url": entry.url, "size": len(server["data"]), "validator": '"old-version"'})
    engine = Engine(state, ProbeStub())
    engine.download_tree(entry, root)
    assert list(work.glob("*.old-*"))
    assert server["requests"] == [None]
    assert engine.target_path(entry, root).read_bytes() == server["data"]
    state.close()


def test_recipient_collection_adopted_only_at_matching_site_path(tmp_path, server):
    state = State(tmp_path / "state")
    root, entry = tmp_path / "downloads", audio(server["url"])
    engine = Engine(state, ProbeStub())
    target = engine.target_path(entry, root)
    target.parent.mkdir(parents=True)
    target.write_bytes(server["data"])
    assert engine.download_tree(entry, root) is True
    assert not server["requests"]
    unrelated = audio(server["url"], "/different/folder/original.mp3")
    assert engine.download_tree(unrelated, root) is False
    assert len(server["requests"]) == 1
    state.close()


def test_existing_conflicting_file_is_never_overwritten(tmp_path, server):
    state = State(tmp_path / "state")
    root, entry = tmp_path / "downloads", audio(server["url"])
    engine = Engine(state, ProbeStub())
    original = engine.target_path(entry, root)
    original.parent.mkdir(parents=True)
    original.write_bytes(b"recipient's unrelated file")
    assert engine.download_tree(entry, root) is False
    assert original.read_bytes() == b"recipient's unrelated file"
    assert engine.target_path(entry, root) != original
    state.close()


def test_untracked_legacy_site_hierarchy_is_reused_in_new_layout(tmp_path,server):
    from vedaboat.model import tree_relative
    state=State(tmp_path/'state');root=tmp_path/'downloads';entry=audio(server['url'])
    old=root/tree_relative(entry.path);old.parent.mkdir(parents=True);old.write_bytes(server['data'])
    engine=Engine(state,ProbeStub())
    assert engine.download_tree(entry,root) is True
    assert not server['requests']
    target=engine.target_path(entry,root)
    assert 'Desire Tree Downloads' in str(target)
    assert old.read_bytes()==target.read_bytes()==server['data']
    state.close()


def test_changed_verified_file_is_not_silently_adopted(tmp_path, server):
    state = State(tmp_path / "state")
    root, entry = tmp_path / "downloads", audio(server["url"])
    engine = Engine(state, ProbeStub())
    engine.download_tree(entry, root)
    old = engine.target_path(entry, root)
    old.write_bytes(b"x" * len(server["data"]))
    assert engine.download_tree(entry, root) is False
    assert engine.target_path(entry, root) != old
    assert old.read_bytes().startswith(b"xxxx")
    state.close()


def test_queue_reopens_pending_and_continues_after_unavailable(tmp_path, server):
    state = State(tmp_path / "state")
    unavailable = Entry("youtube:abcdefghijk", "youtube", "video", "Private", "url", video_id="abcdefghijk", available=False)
    state.make_queue([unavailable, audio(server["url"])], tmp_path / "downloads")
    state.job_status(0, "converting")
    state.close()
    reopened = State(tmp_path / "state")
    assert reopened.queue()[0]["status"] == "pending"
    Engine(reopened, ProbeStub()).run()
    assert [r["status"] for r in reopened.queue()] == ["failed", "done"]
    reopened.retry_failed()
    assert [r["status"] for r in reopened.queue()] == ["pending", "done"]
    reopened.close()


def test_shared_youtube_video_reused_in_second_playlist(tmp_path):
    state = State(tmp_path / "state")
    root = tmp_path / "downloads"
    existing = root / "prior.mp3"
    root.mkdir()
    existing.write_bytes(b"verified source")
    entry = Entry("youtube:abcdefghijk@PLnew", "youtube", "video", "తెలుగు", "url", video_id="abcdefghijk", collection_id="PLnew", collection_title="New", index=4)
    state.remember_file(entry.media_id, existing)
    engine = Engine(state, ProbeStub())
    assert engine.download_youtube(entry, root, 0) is True
    target = engine.target_path(entry, root)
    assert target.read_bytes() == b"verified source"
    assert target.name.startswith("0004 - తెలుగు")
    state.close()


@pytest.fixture
def real_tools(tmp_path):
    path = Path(__file__).resolve().parents[1] / "tools"
    if not (path / "ffmpeg.exe").exists():
        pytest.skip("Run scripts/fetch_tools.py for real conversion tests")
    return Tools(tmp_path / "state", path)


def create_wav(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(22050)
        stream.writeframes(b"\0\0" * 44100)


def test_real_mp3_128_conversion_on_unicode_path(tmp_path, real_tools):
    source, output = tmp_path / "বাংলা భక్తి" / "input.wav", tmp_path / "বাংলা భక్తి" / "output.mp3"
    create_wav(source)
    real_tools.convert(source, output)
    info = real_tools.probe(output)
    assert info["streams"][0]["codec_name"] == "mp3"
    code, text = run_process([str(real_tools.path("ffprobe")), "-v", "error", "-show_entries", "stream=bit_rate", "-of", "json", str(output)])
    assert code == 0
    assert json.loads(text)["streams"][0]["bit_rate"] == "128000"


def test_failed_conversion_keeps_source_then_retries_without_download(tmp_path, real_tools, monkeypatch):
    state = State(tmp_path / "state")
    root = tmp_path / "downloads"
    entry = Entry("youtube:abcdefghijk", "youtube", "video", "A talk", "url", video_id="abcdefghijk", duration=2)
    work = root / ".vedaboat" / "youtube" / entry.video_id
    source = work / "audio.wav"
    create_wav(source)
    atomic_json(work / "download.json", {"source": str(source.resolve())})
    state.make_queue([entry], root)
    original = real_tools.convert

    def fail(*_):
        raise UserError("Conversion failed")

    monkeypatch.setattr(real_tools, "convert", fail)
    engine = Engine(state, real_tools)
    engine.run()
    assert state.queue()[0]["status"] == "failed"
    assert source.is_file()
    monkeypatch.setattr(real_tools, "convert", original)
    state.retry_failed()
    engine.run()
    assert state.queue()[0]["status"] == "done"
    assert engine.target_path(entry, root).exists()
    assert not source.exists()
    state.close()


def test_pause_during_conversion_finishes_current_item_only(tmp_path, real_tools, monkeypatch):
    state = State(tmp_path / "state")
    root = tmp_path / "downloads"
    entries = [Entry("youtube:" + vid, "youtube", "video", "Talk", "url", video_id=vid, duration=2) for vid in ("abcdefghijk", "lmnopqrstuv")]
    work = root / ".vedaboat" / "youtube" / entries[0].video_id
    source = work / "audio.wav"
    create_wav(source)
    atomic_json(work / "download.json", {"source": str(source.resolve())})
    state.make_queue(entries, root)
    engine = Engine(state, real_tools)
    original = real_tools.convert

    def convert(*args):
        engine.request_pause()
        original(*args)

    monkeypatch.setattr(real_tools, "convert", convert)
    engine.run()
    assert [r["status"] for r in state.queue()] == ["done", "pending"]
    state.close()


def test_silent_process_can_be_paused_responsively(tmp_path):
    import sys
    event = threading.Event()
    timer = threading.Timer(.3, event.set)
    timer.start()
    started = time.monotonic()
    with pytest.raises(Paused):
        run_process([sys.executable, "-c", "import time; time.sleep(30)"], cancelled=event)
    assert time.monotonic() - started < 4


def test_real_conversion_on_long_windows_path(tmp_path, real_tools):
    folder = tmp_path / ("long-folder-" * 10) / ("another-folder-" * 8)
    source, output = folder / "original.wav", folder / "converted.mp3"
    create_wav(source)
    assert len(str(output)) > 260
    real_tools.convert(source, output)
    assert real_tools.probe(output)["streams"][0]["codec_name"] == "mp3"


def test_parallel_transfers_pause_all_and_reopen_with_saved_limit(tmp_path,server,monkeypatch):
    server['slow']=True
    state=State(tmp_path/'state');root=tmp_path/'downloads'
    entries=[audio(server['url'],f'/speaker/recording{i}.mp3') for i in range(4)]
    state.make_queue(entries,root,concurrency=3)
    engine=Engine(state,ProbeStub());barrier=threading.Barrier(3);active=0;peak=0;guard=threading.Lock()
    original=engine.download_tree
    def download(entry,destination):
        nonlocal active,peak
        with guard:active+=1;peak=max(peak,active)
        try:
            barrier.wait(timeout=5)
            return original(entry,destination)
        finally:
            with guard:active-=1
    monkeypatch.setattr(engine,'download_tree',download)
    engine.notify=lambda kind,data:engine.request_pause() if kind=='progress' and data['bytes']>=131072 else None
    engine.run()
    assert peak==3 and all(r['status']=='pending' for r in state.queue())
    assert list((root/'.vedaboat'/'partials').glob('*.part'))
    state.put('concurrency',1);state.close()
    state=State(tmp_path/'state');resumed=Engine(state,ProbeStub());resumed.run()
    assert resumed.options['concurrency']==3
    assert all(r['status']=='done' for r in state.queue())
    assert any(r and r.startswith('bytes=') for r in server['requests'])
    assert all(resumed.target_path(e,root).read_bytes()==server['data'] for e in entries)
    state.close()


def test_repeat_download_keeps_original_and_makes_numbered_copy(tmp_path,server):
    state=State(tmp_path/'state');root=tmp_path/'downloads';e=audio(server['url'])
    engine=Engine(state,ProbeStub());state.make_queue([e],root);engine.run()
    original=engine.target_path(e,root)
    state.make_queue([e],root,repeat=True);engine.run();copy=engine.target_path(e,root)
    assert state.queue()[0]['status']=='done' and len(server['requests'])==2
    assert original!=copy and '(2)' in copy.name
    assert original.read_bytes()==copy.read_bytes()==server['data']
    state.make_queue([e],root,repeat=False);engine.run()
    assert state.queue()[0]['status']=='skipped' and len(server['requests'])==2
    assert len(list(root.rglob('*.mp3')))==2
    state.make_queue([e],root,repeat=True);engine.run()
    assert '(3)' in engine.target_path(e,root).name
    assert original.read_bytes()==copy.read_bytes()==server['data']
    state.close()


def test_forced_shared_youtube_video_transfers_once_even_after_reopening(tmp_path,real_tools,monkeypatch):
    state=State(tmp_path/'state');root=tmp_path/'downloads'
    entries=[Entry('youtube:abcdefghijk@'+pid,'youtube','video','Talk','url',video_id='abcdefghijk',
                   channel_id='channel',channel_title='Channel',collection_id=pid,collection_title=pid,index=1,duration=2)
             for pid in ('PLone','PLtwo')]
    prior=root/'prior.mp3';prior.parent.mkdir(parents=True);prior.write_bytes(b'old verified')
    state.remember_file(entries[0].artifact_id,prior)
    calls=[]
    def yt(args,**kw):
        calls.append(args)
        source=root/'.vedaboat'/'youtube'/'abcdefghijk'/'audio.wav';create_wav(source)
        kw['on_line']('VBFILE|'+str(source));return 0,''
    monkeypatch.setattr(engine_module,'run_process',yt)
    state.make_queue(entries,root,concurrency=2,repeat=True)
    engine=Engine(state,real_tools);engine.run()
    assert [r['status'] for r in state.queue()]==['done','skipped']
    assert len(calls)==1 and prior.read_bytes()==b'old verified'
    outputs=[engine.target_path(e,root) for e in entries]
    assert outputs[0]!=outputs[1] and outputs[0].read_bytes()==outputs[1].read_bytes()
    state.job_status(1,'pending');state.close();state=State(tmp_path/'state')
    Engine(state,real_tools).run()
    assert len(calls)==1 and state.queue()[1]['status']=='skipped'
    state.close()


def test_parallel_audio_sources_convert_serially_and_pause_keeps_waiting_source(tmp_path,real_tools,monkeypatch):
    state=State(tmp_path/'state');root=tmp_path/'downloads'
    entries=[Entry('youtube:'+vid,'youtube','video','Talk','url',video_id=vid,duration=2)
             for vid in ('abcdefghijk','lmnopqrstuv')]
    for e in entries:
        source=root/'.vedaboat'/'youtube'/e.video_id/'audio.wav';create_wav(source)
        atomic_json(source.parent/'download.json',{'source':str(source.resolve())})
    state.make_queue(entries,root,concurrency=2)
    engine=Engine(state,real_tools);original=real_tools.convert;active=0;peak=0
    def convert(*args):
        nonlocal active,peak
        active+=1;peak=max(peak,active)
        try:
            engine.request_pause();time.sleep(.15);return original(*args)
        finally:active-=1
    monkeypatch.setattr(real_tools,'convert',convert);engine.run()
    assert peak==1
    statuses=[r['status'] for r in state.queue()]
    assert sorted(statuses)==['done','pending']
    pending=entries[statuses.index('pending')]
    assert (root/'.vedaboat'/'youtube'/pending.video_id/'audio.wav').is_file()
    monkeypatch.setattr(real_tools,'convert',original);engine.pause.clear();engine.run()
    assert all(r['status']=='done' for r in state.queue())
    state.close()
