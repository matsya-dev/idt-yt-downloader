from vedaboat import license_notice
from vedaboat.state import State


def test_runtime_terms_are_remembered_only_after_explicit_agreement(monkeypatch, tmp_path):
    folder = tmp_path / 'bundle' / 'third-party'
    folder.mkdir(parents=True)
    (folder / 'Python-Windows-CRT-license.txt').write_text('Recorded runtime conditions')
    monkeypatch.setattr(license_notice, 'application_directory', lambda: folder.parent)
    state = State(tmp_path / 'profile')
    calls = []
    monkeypatch.setattr(license_notice, 'show_runtime_terms', lambda *_: calls.append(True) or False)
    assert not license_notice.ensure_runtime_terms(None, state)
    assert state.get('runtime_terms_accepted') is None
    monkeypatch.setattr(license_notice, 'show_runtime_terms', lambda *_: calls.append(True) or True)
    assert license_notice.ensure_runtime_terms(None, state)
    assert license_notice.ensure_runtime_terms(None, state)
    assert len(calls) == 2
    state.close()


def test_changed_conditions_require_a_new_agreement(monkeypatch, tmp_path):
    folder = tmp_path / 'third-party'
    folder.mkdir()
    text = folder / 'Python-Windows-CRT-license.txt'
    text.write_text('First conditions')
    monkeypatch.setattr(license_notice, 'application_directory', lambda: tmp_path)
    monkeypatch.setattr(license_notice, 'show_runtime_terms', lambda *_: True)
    state = State(tmp_path / 'profile')
    assert license_notice.ensure_runtime_terms(None, state)
    text.write_text('Changed conditions')
    monkeypatch.setattr(license_notice, 'show_runtime_terms', lambda *_: False)
    assert not license_notice.ensure_runtime_terms(None, state)
    state.close()
