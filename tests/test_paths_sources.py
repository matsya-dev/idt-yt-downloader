from pathlib import Path
from urllib.parse import quote

import pytest

from vedaboat.engine import Engine
from vedaboat.model import Entry, UserError, confined, safe_component, tree_path, tree_relative, tree_url, youtube_url
from vedaboat.selection import Selection
from vedaboat.sources import DesireTree, YouTube
from vedaboat.state import State


def test_desire_tree_route_has_one_identity():
    path = "/02_-_ISKCON_Swamis/বাংলা/Talk + 01.mp3"
    assert tree_path(tree_url(path)) == tree_path("https://audio.iskcondesiretree.com" + quote(path)) == path
    assert tree_relative(path) == Path("02_-_ISKCON_Swamis") / "বাংলা" / "Talk + 01.mp3"


@pytest.mark.parametrize("value", ["/a/../b.mp3", "https://evil.test/index.php?f=/a", "/a\\..\\b", "https://audio.iskcondesiretree.com:8000/a", "/a/./b", "/a/CON:bad.mp3"])
def test_reject_unsafe_desire_tree_paths(value):
    with pytest.raises(UserError):
        tree_path(value)


def test_windows_names_are_distinct_and_unicode_is_preserved():
    assert safe_component("భక్తి · ভক্তি · பக்தி") == "భక్తి · ভক্তি · பக்தி"
    assert safe_component("CON.mp3") == "_CON.mp3"
    assert tree_relative("/a/a?.mp3") != tree_relative("/a/a*.mp3")
    assert tree_relative("/a/" + "x" * 260 + ".mp3").suffix == ".mp3"


def test_confined_blocks_escape(tmp_path):
    with pytest.raises(UserError):
        confined(tmp_path, Path("../elsewhere"))


@pytest.mark.parametrize("url", ["https://youtu.be/abcdefghijk?t=3", "https://youtube.com/watch?v=abcdefghijk", "https://youtube.com/shorts/abcdefghijk"])
def test_video_links_normalize(url):
    assert youtube_url(url) == ("https://www.youtube.com/watch?v=abcdefghijk", "video")


def test_playlist_context_wins_over_watch_link():
    assert youtube_url("https://youtube.com/watch?v=abcdefghijk&list=PL123")[0] == "https://www.youtube.com/playlist?list=PL123"


def test_nonlatin_channel_switches_views():
    canonical, kind = youtube_url("https://www.youtube.com/@భక్తివికాసస్వామి/videos", "playlists")
    assert kind == "channel"
    assert canonical.endswith("/playlists")
    assert quote("భక్తివికాసస్వామి") in canonical


@pytest.mark.parametrize("url", ["file:///C:/private", "https://youtube.com.evil.test/watch?v=abcdefghijk", "https://youtube.com/results?search_query=x", "https://youtu.be/not-an-id", "https://youtube.com:9000/@channel", "https://x@youtube.com/@channel"])
def test_invalid_youtube_links(url):
    with pytest.raises(UserError):
        youtube_url(url)


def test_parser_ignores_breadcrumbs_counts_and_external_links():
    html = '''<title>Audio</title>
    <a href="index.php?q=f&f=/a">Parent</a>
    <a href="index.php?q=f&f=/a/b"><img src="x"></a>
    <a href="index.php?q=f&f=/a/b">Folder B</a>
    <a href="index.php?q=f&f=/a/b">3&nbsp;folders</a>
    <a href="index.php?q=f&f=/a/b/deeper">Not a direct child</a>
    <a href="/a/a%20%2B%20talk.mp3">Listen</a>
    <a href="https://external.test/a/wrong.mp3">Wrong</a>'''
    entries = DesireTree().parse(html, "/a").entries
    assert len(entries) == 2
    assert entries[0].title == "Folder B"
    assert entries[1].title == "a + talk.mp3"
    assert entries[1].url.endswith("/a/a%20%2B%20talk.mp3")


def test_parser_recognizes_download_routes_and_errors():
    entry = DesireTree().parse('<a href="index.php?q=d&f=%2Fa%2Ftest.mp3">Download</a>', "/a").entries[0]
    assert entry.path == "/a/test.mp3"
    with pytest.raises(UserError):
        DesireTree().parse("<title>Audio: File not found</title>", "/a")


def test_playlist_preserves_order_unavailability_and_id():
    info = {"id": "PLsame", "title": "ভক্তি", "channel_id": "UCchannel", "channel": "Channel", "entries": [
        {"id": "abcdefghijk", "title": "Same title", "duration": 60},
        {"id": "lmnopqrstuv", "title": "[Private video]", "availability": "private"},
        {"id": "zyxwvutsrqp", "title": "Same title", "playlist_index": 7}]}
    collection = YouTube(None).parse(info, "https://youtube.com/playlist?list=PLsame", "playlist")
    assert [e.index for e in collection.entries] == [1, 2, 7]
    assert not collection.entries[1].available
    assert collection.entries[0].estimated_size == 960000
    assert collection.entries[0].key != collection.entries[2].key


def test_channel_playlists_are_containers():
    collection = YouTube(None).parse({"id": "UCchannel", "entries": [{"id": "PLone", "title": "One", "url": "https://youtube.com/playlist?list=PLone"}]}, "url", "channel", "playlists")
    assert collection.entries[0].container


def test_shared_video_has_same_media_identity_but_playlist_occurrences():
    yt = YouTube(None)
    a = yt.parse({"id": "PLone", "entries": [{"id": "abcdefghijk", "title": "One"}]}, "url", "playlist").entries[0]
    b = yt.parse({"id": "PLtwo", "entries": [{"id": "abcdefghijk", "title": "One"}]}, "url", "playlist").entries[0]
    assert a.media_id == b.media_id
    assert a.key != b.key


def test_stable_playlist_path_survives_renaming(tmp_path):
    state = State(tmp_path / "data")
    engine = Engine(state, None)
    e = Entry("youtube:abcdefghijk@PLone", "youtube", "video", "Original", "url", video_id="abcdefghijk", collection_id="PLone", collection_title="Playlist", channel_id="UCone", channel_title="Channel", index=1)
    first = engine.target_path(e, tmp_path / "downloads")
    e.title, e.channel_title, e.collection_title = "Renamed", "Renamed", "Renamed"
    assert engine.target_path(e, tmp_path / "downloads") == first
    state.close()


def test_folder_partial_selection_and_search_independence():
    selection = Selection()
    folder = Entry("tree:/a", "tree", "folder", "A", "url", path="/a")
    children = [Entry("tree:/a/one.mp3", "tree", "audio", "one", "url", path="/a/one.mp3"), Entry("tree:/a/sub/two.mp3", "tree", "audio", "two", "url", path="/a/sub/two.mp3")]
    selection.accept_collection(folder, children)
    assert selection.state(folder) == "checked"
    selection.deselect(children[0])
    assert selection.state(folder) == "partial"
    assert children[1].key in selection.entries
    selection.deselect(folder)
    assert not selection.entries


def test_deselection_during_discovery_is_respected():
    selection = Selection()
    folder = Entry("tree:/a", "tree", "folder", "A", "url", path="/a")
    entry = Entry("tree:/a/one.mp3", "tree", "audio", "one", "url", path="/a/one.mp3")
    selection.deselect(entry)
    selection.accept_collection(folder, [entry])
    assert not selection.entries


def test_no_public_playlists_is_an_empty_collection(monkeypatch):
    import vedaboat.sources as sources

    class Tools:
        def yt_args(self):
            return []

    monkeypatch.setattr(sources, "run_process", lambda *_args, **_kw: (1, "ERROR: This channel does not have a playlists tab\nnull"))
    collection = YouTube(Tools()).browse("https://youtube.com/@example", "playlists")
    assert collection.entries == []
    assert collection.notice == "This channel has no public playlists."
