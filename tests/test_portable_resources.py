from pathlib import Path
import sys

from vedaboat.tools import application_directory, Tools
from vedaboat.state import State


def test_single_file_uses_extracted_resources_and_external_profile(monkeypatch, tmp_path):
    extracted = tmp_path / 'temporary bundle'
    (extracted / 'assets').mkdir(parents=True)
    (extracted / 'tools').mkdir()
    (extracted / 'tools' / 'qjs.exe').write_bytes(b'bundled')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(extracted), raising=False)
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'different folder' / 'Downloader.exe'))
    assert application_directory() == extracted
    state = State(tmp_path / 'persistent profile')
    state.put('destination', 'saved destination')
    tools = Tools(state.directory)
    assert tools.path('qjs') == extracted / 'tools' / 'qjs.exe'
    assert tools.updates.is_relative_to(state.directory)
    state.close()
    (extracted / 'tools' / 'qjs.exe').unlink()
    reopened = State(tmp_path / 'persistent profile')
    assert reopened.get('destination') == 'saved destination'
    reopened.close()


def test_legacy_folder_resources_are_still_supported(monkeypatch, tmp_path):
    exe = tmp_path / 'old app'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(exe / '_internal'), raising=False)
    monkeypatch.setattr(sys, 'executable', str(exe / 'Downloader.exe'))
    assert application_directory() == exe


def test_updated_helper_stays_outside_single_file_extraction(monkeypatch, tmp_path):
    extracted = tmp_path / 'extracted'
    (extracted / 'assets').mkdir(parents=True)
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(extracted), raising=False)
    tools = Tools(tmp_path / 'profile')
    generation = tools.updates / 'recorded-generation'
    generation.mkdir(parents=True)
    (generation / 'qjs.exe').write_bytes(b'updated')
    (tools.updates / 'current.json').write_text('{"generation":"recorded-generation"}')
    assert tools.path('qjs') == generation / 'qjs.exe'
    assert not tools.path('qjs').is_relative_to(extracted)
