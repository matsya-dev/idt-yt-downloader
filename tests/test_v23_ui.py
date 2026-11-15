"""User-visible navigation, theme and compact-layout regressions for the rename."""
from types import SimpleNamespace
from tkinter import ttk
import pytest

from test_ui import app, tk_root, many_recordings
from vedaboat.model import Collection, Entry
from vedaboat.theme import DARK, LIGHT


@pytest.mark.parametrize('state',[0,8,16])
def test_up_down_symmetry_ignores_numlock_modifier_states(app,monkeypatch,state):
    entries,nodes=many_recordings(app)
    app.toggle(entries[1],True);app.browser.focus_only(nodes[3])
    def unexpected():raise AssertionError('Ordinary Up navigated outside the list')
    monkeypatch.setattr(app,'up',unexpected)
    for key,target in [('Up',2),('Down',3),('Up',2),('Up',1),('Up',0),('Up',0)]:
        app.browser.key(SimpleNamespace(keysym=key,state=state))
        assert app.files.focus()==nodes[target]
        assert set(app.selected().entries)=={entries[1].key}
        assert 'keyboard_focus' in app.files.item(nodes[target],'tags')
    assert app.files.bind('<Alt-Up>') and app.files.bind('<Alt-Left>')


def test_native_tk_dispatch_distinguishes_numlock_from_alt_up(app,monkeypatch):
    entries,nodes=many_recordings(app);calls=[]
    monkeypatch.setattr(app,'up',lambda:calls.append('up'))
    app.root.deiconify();app.root.update();app.files.focus_force();app.root.update()
    try:
        for state in (0,8):
            app.browser.focus_only(nodes[3])
            app.files.event_generate('<KeyPress-Up>',state=state,when='now')
            assert app.files.focus()==nodes[2] and not calls
            assert not app.selected().entries
        app.files.event_generate('<Alt-KeyPress-Up>',when='now')
        assert calls==['up']
    finally:app.root.withdraw()


def test_first_arrow_on_folder_never_discovers_or_ticks(app,monkeypatch):
    folder=Entry('tree:/a','tree','folder','A','url',path='/a')
    child=Entry('tree:/a/one.mp3','tree','audio','One','child',path='/a/one.mp3',size=10)
    app.collection=Collection('test:folder','A',[folder],'tree')
    calls=[]
    monkeypatch.setattr(app,'fetch',lambda *args:(calls.append(args),Collection('url','A',[child],'tree'))[1])
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:done(fn()))
    app.render_files();node=app.browser.visible_ids[0];app.files.focus('')
    app.browser.key(SimpleNamespace(keysym='Down',state=0))
    assert app.files.focus()==node and not calls and not app.selected().entries
    app.browser.key(SimpleNamespace(keysym='Right',state=0))
    assert len(calls)==1 and app.files.item(node,'open')
    app.browser.key(SimpleNamespace(keysym='Right',state=0))
    assert app.files.focus()==node and len(calls)==1
    app.browser.key(SimpleNamespace(keysym='Left',state=0))
    app.browser.key(SimpleNamespace(keysym='Left',state=0))
    assert app.files.focus()==node and not app.files.item(node,'open')
    assert not app.selected().entries and not app.selected().loading


def test_left_right_on_recording_does_not_move_or_tick(app):
    entries,nodes=many_recordings(app);app.browser.focus_only(nodes[2])
    for key in ('Left','Right'):
        app.browser.key(SimpleNamespace(keysym=key,state=0))
        assert app.files.focus()==nodes[2] and not app.selected().entries


def test_shift_range_starts_from_keyboard_focus_and_space_only_toggles_focus(app):
    entries,nodes=many_recordings(app)
    app.browser.focus_only(nodes[1]);app.browser.key(SimpleNamespace(keysym='Down',state=1))
    app.browser.key(SimpleNamespace(keysym='Down',state=1))
    assert set(app.selected().entries)=={e.key for e in entries[1:4]}
    app.browser.key(SimpleNamespace(keysym='Up',state=1))
    assert set(app.selected().entries)=={e.key for e in entries[1:3]}
    app.browser.space()
    assert set(app.selected().entries)=={entries[1].key}


def test_focus_survives_loading_refresh_and_filter_without_ticking(app):
    entries,nodes=many_recordings(app)
    app.toggle(entries[0],True);app.browser.focus_only(nodes[3])
    app.loading=True;app.render_files();app.loading=False;app.render_files()
    assert app.files.focus()==nodes[3]
    app.search_box.set('Recording 1')
    assert app.files.focus()==nodes[1]
    app.search_box.set()
    assert app.files.focus()==nodes[1]
    assert set(app.selected().entries)=={entries[0].key}


def test_collapsing_focused_descendant_restores_visible_parent(app,monkeypatch):
    folder=Entry('tree:/a','tree','folder','A','url',path='/a')
    child=Entry('tree:/a/one.mp3','tree','audio','One','child',path='/a/one.mp3',size=10)
    app.collection=Collection('test:folder','A',[folder],'tree')
    monkeypatch.setattr(app,'fetch',lambda *_:Collection('url','A',[child],'tree'))
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:done(fn()))
    app.render_files();node=app.browser.visible_ids[0];app.browser.expand(node)
    app.browser.focus_only(app.browser.visible_ids[-1]);app.browser.collapse_all()
    assert app.files.focus()==node and not app.selected().entries


def test_system_theme_default_live_updates_and_manual_override(app,monkeypatch):
    import vedaboat.ui as ui_module
    monkeypatch.setattr(ui_module,'system_is_dark',lambda:False)
    assert app.theme_mode.get()=='System'
    app.set_theme();assert app.colors==LIGHT
    monkeypatch.setattr(ui_module,'system_is_dark',lambda:True)
    app.poll_system_theme();assert app.colors==DARK
    assert app.state.get('theme_mode')=='System'
    app.theme_mode.set('Light');app.set_theme()
    app.poll_system_theme();assert app.colors==LIGHT
    assert app.state.get('theme_mode')=='Light'
    assert app.colors['focus']!=app.colors['selected']
    assert ttk.Style(app.root).lookup('Treeview','background')==LIGHT['bg']


def test_header_controls_and_hidden_selected_count_fit_compact_window(app):
    entries,nodes=many_recordings(app)
    app.toggle(entries[0],True);app.toggle(entries[1],True)
    app.search_box.set('Recording 0');app.root.deiconify();app.root.geometry('800x620+20+20');app.root.update()
    try:
        assert app.count['text']=='1 shown' and app.selection_label['text']=='2 selected'
        assert app.clear_button.winfo_rootx()>app.select_all_check.winfo_rootx()+app.select_all_check.winfo_width()
        assert app.selection_label.winfo_rootx()>app.count.winfo_rootx()
        assert app.selection_label.winfo_rootx()+app.selection_label.winfo_width()<=app.root.winfo_rootx()+app.root.winfo_width()
        assert app.files.winfo_height()>=120
    finally:app.root.withdraw()


def test_partial_parent_makes_select_all_partial(app):
    folder=Entry('tree:/a','tree','folder','A','url',path='/a')
    first=Entry('tree:/a/one.mp3','tree','audio','One','url',path='/a/one.mp3',size=10)
    app.collection=Collection('test:folder','A',[folder],'tree')
    app.selected().members[folder.key]={first.key,'tree:/a/two.mp3'}
    app.toggle(first,True);app.render_files()
    assert 'alternate' in app.select_all_check.state()
