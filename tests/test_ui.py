from pathlib import Path
import tkinter as tk
from types import SimpleNamespace

import pytest

from vedaboat.model import Collection, Entry, TREE_HOME
from vedaboat.state import State
from vedaboat.ui import App
from vedaboat import APP_NAME

REAL_LOAD = App.load


def cancel_timers(root):
    # Cancel through the widget that registered each Python callback. Cancelling
    # child-owned tooltip callbacks through root leaves stale Tcl command names.
    widgets=[]
    def collect(widget):
        widgets.append(widget)
        for child in widget.winfo_children():collect(child)
    collect(root)
    for after_id in root.tk.call('after','info'):
        script,kind=root.tk.call('after','info',after_id)
        if kind!='timer':continue
        name=root.tk.splitlist(script)[0]
        owner=next((w for w in widgets if name in (getattr(w,'_tclCommands',None) or [])),None)
        if owner is not None:owner.after_cancel(after_id)
        else:root.tk.call('after','cancel',after_id)


@pytest.fixture(scope="module")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def app(tmp_path, monkeypatch, tk_root):
    root = tk_root
    state = State(tmp_path / "state")
    monkeypatch.setattr(App, "load", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(App, "fetch", lambda self, url, source, *_args, **_kwargs: Collection(url,'Test',[],source))
    ui = App(root, state)
    cancel_timers(root)
    yield ui
    ui.closing = True
    ui.executor.shutdown(wait=True, cancel_futures=True)
    cancel_timers(root)
    for widget in root.winfo_children():
        widget.destroy()
    root.unbind('<Configure>')
    state.close()


def sample_collection():
    return Collection("test:collection", "Test", [
        Entry("tree:/a.mp3", "tree", "audio", "Hearing", "url", path="/a.mp3", size=1234),
        Entry("tree:/b.mp3", "tree", "audio", "Chanting", "url", path="/b.mp3", size=2345)], "tree")


def test_search_keeps_selection_and_empty_placeholder_shows_all(app):
    app.collection = sample_collection()
    app.toggle(app.collection.entries[0], True)
    app.search_box.set("Chanting")
    assert [e.title for e in app.visible] == ["Chanting"]
    assert len(app.selected().entries) == 1
    app.search_box.set()
    assert len(app.visible) == 2
    app.show_selected()
    assert [e.title for e in app.visible] == ["Hearing"]


def test_select_all_applies_only_to_filtered_list(app):
    app.collection = sample_collection()
    app.search_box.set("Chanting")
    app.select_all_var.set(True)
    app.select_all()
    assert list(app.selected().entries) == ["tree:/b.mp3"]
    app.search_box.set()
    assert len(app.visible) == 2


def test_new_profile_starts_unselected_and_destination_is_remembered(app):
    assert not app.selected().entries
    assert str(app.main_button["state"]) == "disabled"
    assert app.root.title() == APP_NAME
    app.state.put("destination", "C:/Music")
    assert app.state.get("destination") == "C:/Music"


def test_unfinished_queue_has_resume_and_does_not_allow_replacement(app, tmp_path):
    app.state.make_queue(sample_collection().entries, tmp_path / "downloads")
    app.refresh_download()
    assert app.main_button["text"] == "Resume"
    app.toggle(sample_collection().entries[0], True)
    assert not app.selected().entries
    with pytest.raises(RuntimeError):
        app.state.make_queue(sample_collection().entries[:1], tmp_path / "different")


def many_recordings(app):
    entries=[Entry(f'tree:/file{i}.mp3','tree','audio',f'Recording {i}','url',path=f'/file{i}.mp3',size=1000) for i in range(6)]
    app.collection=Collection('test:recordings','Test',entries,'tree');app.render_files()
    return entries,list(app.browser.visible_ids)


def test_ctrl_click_and_shift_range_select_downloads(app):
    entries,nodes=many_recordings(app)
    app.browser.select(nodes[0]);app.browser.select(nodes[2],ctrl=True)
    assert set(app.selected().entries)=={entries[0].key,entries[2].key}
    app.browser.select(nodes[4],shift=True)
    assert set(app.selected().entries)=={e.key for e in entries[2:5]}
    app.browser.select(nodes[3],ctrl=True)
    assert set(app.selected().entries)=={entries[2].key,entries[4].key}


def test_keyboard_range_ctrl_focus_and_space(app):
    entries,nodes=many_recordings(app)
    app.browser.select(nodes[1])
    app.browser.key(SimpleNamespace(keysym='Down',state=1))
    assert set(app.selected().entries)=={entries[1].key,entries[2].key}
    app.browser.key(SimpleNamespace(keysym='Down',state=4))
    assert app.files.focus()==nodes[3]
    assert set(app.selected().entries)=={entries[1].key,entries[2].key}
    app.browser.space()
    assert set(app.selected().entries)=={entries[1].key,entries[2].key,entries[3].key}


def test_filter_preserves_checked_recordings_outside_range(app):
    entries,nodes=many_recordings(app)
    app.browser.select(nodes[0])
    app.search_box.set('Recording 4')
    app.browser.select(app.browser.visible_ids[0])
    assert set(app.selected().entries)=={entries[0].key,entries[4].key}


@pytest.mark.parametrize('kind,source',[('folder','tree'),('playlist','youtube')])
def test_inline_expand_collapse_is_lazy_and_does_not_select(app,monkeypatch,kind,source):
    folder=Entry('container','tree' if source=='tree' else 'youtube',kind,'Collection','url',path='/a')
    child=Entry('child',source,'audio' if source=='tree' else 'video','Child','url',path='/a/child.mp3',size=100)
    app.source=source;app.collection=Collection('url','Test',[folder],source)
    calls=[]
    def fetch(*args):
        calls.append(args);return Collection('url','Children',[child],source)
    monkeypatch.setattr(app,'fetch',fetch)
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:done(fn()))
    app.render_files();node=app.browser.visible_ids[0]
    assert not calls and not app.selected().entries
    app.browser.expand(node)
    assert len(calls)==1 and len(app.visible)==2 and not app.selected().entries
    app.browser.expand(node)
    assert len(app.visible)==1
    app.browser.expand(node)
    assert len(calls)==1 and len(app.visible)==2


@pytest.mark.parametrize('width,height,source',[(800,620,'tree'),(800,620,'youtube'),(1040,740,'tree')])
def test_restored_window_preserves_list_and_bottom_controls(app,width,height,source):
    app.root.deiconify();app.root.update()
    app.source=source;app.sidebar_render()
    if source=='youtube':app.youtube_modes.pack(side='right',padx=5)
    app.root.geometry(f'{width}x{height}+20+20');app.root.update()
    try:
        assert app.files.winfo_height()>=120
        assert app.main_button.winfo_rooty()+app.main_button.winfo_height()<=app.root.winfo_rooty()+app.root.winfo_height()
        assert app.folder_button.winfo_rootx()+app.folder_button.winfo_width()<=app.root.winfo_rootx()+app.root.winfo_width()
    finally:
        app.root.withdraw()


def test_quality_default_setting_and_estimates(app):
    assert app.quality.get()==128
    app.source='youtube'
    app.collection=Collection('url','YouTube',[Entry('vid','youtube','video','Video','url',video_id='abcdefghijk',duration=600)],'youtube')
    app.toggle(app.collection.entries[0],True)
    app.set_quality(320)
    assert app.state.get('youtube_quality')==320
    assert '22.9 MB' in app.summary['text']


def test_arrow_down_starts_at_first_row(app):
    entries,nodes=many_recordings(app)
    app.files.focus('')
    app.browser.key(SimpleNamespace(keysym='Down',state=0))
    assert app.files.focus()==nodes[0] and not app.selected().entries


def test_checkbox_click_toggles_highlighted_group(app):
    entries,nodes=many_recordings(app)
    app.browser.all();app.root.deiconify();app.root.update()
    try:
        box=app.files.bbox(nodes[0],'#0')
        app.browser.click(SimpleNamespace(x=box[0]+28,y=box[1]+box[3]//2,state=0))
        assert not app.selected().entries
    finally:
        app.root.withdraw()


def test_native_arrow_single_click_expands_and_collapses(app,monkeypatch):
    folder=Entry('folder','tree','folder','Folder','url',path='/a')
    child=Entry('child','tree','audio','Child','url',path='/a/child.mp3',size=10)
    app.collection=Collection('url','Test',[folder],'tree')
    monkeypatch.setattr(app,'fetch',lambda *_:Collection('url','Children',[child],'tree'))
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:done(fn()))
    app.render_files();app.root.deiconify();app.root.update()
    try:
        node=app.browser.visible_ids[0];box=app.files.bbox(node,'#0')
        event=SimpleNamespace(x=box[0]+8,y=box[1]+box[3]//2,state=0)
        assert 'indicator' in app.files.identify_element(event.x,event.y)
        app.browser.click(event)
        assert len(app.visible)==2 and not app.selected().entries
        app.browser.click(event)
        assert len(app.visible)==1
    finally:
        app.root.withdraw()


def test_click_selected_deselects_only_it_and_ctrl_click_includes_parent(app,monkeypatch):
    entries,nodes=many_recordings(app)
    app.browser.select(nodes[0]);app.browser.select(nodes[2],ctrl=True)
    app.browser.select(nodes[0],click=True)
    assert set(app.selected().entries)=={entries[2].key}
    folder=Entry('tree:/parent','tree','folder','Parent','url',path='/parent')
    leaf=Entry('tree:/parent/file.mp3','tree','audio','File','url',path='/parent/file.mp3',size=10)
    app.collection.entries.append(folder)
    monkeypatch.setattr(app,'fetch',lambda *_:Collection('url','Parent',[leaf],'tree'))
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:done(fn()))
    app.render_files();node=next(n for n,e in app.browser.rows.items() if e==folder)
    app.browser.select(node,ctrl=True,click=True)
    assert set(app.selected().entries)=={entries[2].key,leaf.key}
    app.browser.select(node,ctrl=True,click=True)
    assert set(app.selected().entries)=={entries[2].key}


def test_root_is_tickable_and_arrows_only_focus_or_expand_without_wrapping(app,monkeypatch):
    parent=Entry('tree:/a','tree','folder','A','url',path='/a')
    child=Entry('tree:/a/one.mp3','tree','audio','One','url',path='/a/one.mp3',size=10)
    app.collection=Collection(TREE_HOME,'All Desire Tree audio',[parent],'tree')
    monkeypatch.setattr(app,'fetch',lambda url,*_:Collection(url,'Collection',[child] if url=='url' else [parent],'tree'))
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:done(fn()))
    app.render_files();root,node=app.browser.visible_ids
    app.browser.expand(node);childnode=app.browser.visible_ids[-1]
    app.browser.select(childnode)
    app.browser.key(SimpleNamespace(keysym='Up',state=0))
    assert app.files.focus()==node and set(app.selected().entries)=={child.key}
    app.browser.key(SimpleNamespace(keysym='Left',state=0)) # collapse
    app.browser.key(SimpleNamespace(keysym='Left',state=0)) # already collapsed: stay
    assert app.files.focus()==node
    app.browser.key(SimpleNamespace(keysym='Up',state=0))
    assert app.files.focus()==root
    assert set(app.selected().entries)=={child.key}
    app.browser.space()
    assert app.selected().state(app.browser.rows[root])=='unchecked'
    app.browser.space()
    assert app.selected().state(app.browser.rows[root])=='checked'
    app.browser.collapse_all()
    assert app.selected().state(parent)=='checked'


def test_cancel_discovery_does_not_reappear_and_spinner_animates(app,monkeypatch):
    folder=Entry('tree:/a','tree','folder','A','url',path='/a')
    leaf=Entry('tree:/a/one.mp3','tree','audio','One','url',path='/a/one.mp3',size=10)
    app.collection=Collection('test:folder','A',[folder],'tree');app.render_files()
    jobs=[]
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:jobs.append((fn,done)))
    app.toggle(folder,True);assert app.selected().state(folder)=='loading'
    app.browser.animate();assert app.browser.spin_frame==1
    node=app.browser.visible_ids[0]
    assert app.files.item(node,'image')
    app.toggle(folder,False)
    jobs[0][1](([leaf],{folder.key:{leaf.key}}))
    assert not app.selected().entries and not app.selected().loading


def test_loading_and_error_are_inside_list(app):
    app.loading=True;app.render_files()
    assert any('Loading recordings' in app.files.item(n,'text') for n in app.files.get_children())
    app.loading=False;app.list_message='Could not load. Try Refresh.';app.collection=None;app.render_files()
    assert any('Try Refresh' in app.files.item(n,'text') for n in app.files.get_children())


def test_dark_mode_saved_applies_to_lists_and_dialogs_and_restores(app):
    from vedaboat.theme import DARK,LIGHT
    from tkinter import ttk
    app.theme_mode.set('Dark');app.set_theme()
    assert app.state.get('theme_mode') == 'Dark'
    assert ttk.Style(app.root).lookup('Treeview','background')==DARK['bg']
    app.help();app.settings()
    dialogs=[w for w in app.root.winfo_children() if isinstance(w,tk.Toplevel)]
    assert dialogs and all(w.cget('bg')==DARK['bg'] for w in dialogs)
    assert all(getattr(w,'vedaboat_colors',None)==DARK for w in dialogs)
    app.theme_mode.set('Light');app.set_theme()
    assert ttk.Style(app.root).lookup('Treeview','background')==LIGHT['bg']
    assert app.quality.get()==128 and app.concurrency.get()==1 and not app.repeat.get()


def test_add_shortcut_follows_shortcuts_and_guidance_is_removed(app):
    app.sidebar_render();app.root.deiconify();app.root.update()
    try:
        assert not hasattr(app,'sidebar_hint')
        assert app.shortcuts_inner.pack_slaves()[-1] is app.add_shortcut_button
        last=app.shortcut_buttons[-1]
        assert app.add_shortcut_button.winfo_y() >= last.winfo_y()+last.winfo_height()+10
        assert any(i['name']=='Bhakti Vikasa Swami' for i in app.shortcuts.items)
    finally:
        app.root.withdraw()


def test_partial_parent_and_rechecking_parent_restores_excluded_children(app,monkeypatch):
    folder=Entry('tree:/a','tree','folder','A','url',path='/a')
    leaves=[Entry('tree:/a/'+str(i)+'.mp3','tree','audio',str(i),'url',path='/a/'+str(i)+'.mp3',size=10) for i in range(2)]
    monkeypatch.setattr(app,'fetch',lambda *_:Collection('url','A',leaves,'tree'))
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:done(fn()))
    app.toggle(folder,True);assert app.selected().state(folder)=='checked'
    app.toggle(leaves[0],False);assert app.selected().state(folder)=='partial'
    app.toggle(folder,True);assert app.selected().state(folder)=='checked'
    assert set(app.selected().entries)=={e.key for e in leaves}


def test_deselect_channel_root_cancels_playlist_discovery(app,monkeypatch):
    app.source='youtube'
    playlist=Entry('playlist:PLqa','youtube','playlist','Playlist','https://www.youtube.com/playlist?list=PLqa',collection_id='PLqa')
    app.collection=Collection('https://www.youtube.com/@test/playlists','Channel',[playlist],'youtube')
    app.mode.set('playlists');app.render_files();root=app.browser.rows[app.browser.visible_ids[0]]
    jobs=[];monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:jobs.append((fn,done)))
    app.toggle(playlist,True);token=app.selection_tasks[playlist.key]
    app.toggle(root,False)
    assert token.is_set() and not app.selected().loading
    leaf=Entry('youtube:abcdefghijk@PLqa','youtube','video','Talk','url',video_id='abcdefghijk',collection_id='PLqa')
    jobs[0][1](([leaf],{playlist.key:{leaf.key}}))
    assert not app.selected().entries


def test_expansion_failure_is_shown_inside_branch(app,monkeypatch):
    from vedaboat.model import UserError
    folder=Entry('tree:/a','tree','folder','A','url',path='/a')
    app.collection=Collection('test:folder','A',[folder],'tree');app.render_files()
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:fail(UserError('Connection interrupted. Expand again to retry.')))
    node=app.browser.visible_ids[0];app.browser.expand(node)
    assert app.files.item(node,'open')
    assert 'Connection interrupted' in app.files.item(app.files.get_children(node)[0],'text')


def test_filtered_select_all_does_not_tick_context_root_or_hidden_recordings(app):
    app.collection=sample_collection();app.collection.url=TREE_HOME
    app.search_box.set('Chanting')
    app.select_all_var.set(True);app.select_all()
    assert set(app.selected().entries)=={'tree:/b.mp3'}
    assert app.select_all_var.get()


def test_search_expanded_branches_can_collapse_and_reopen(app,monkeypatch):
    folder=Entry('tree:/a','tree','folder','A','url',path='/a')
    leaf=Entry('tree:/a/one.mp3','tree','audio','Hearing','url',path='/a/one.mp3',size=10)
    app.collection=Collection('test:folder','A',[folder],'tree')
    monkeypatch.setattr(app,'fetch',lambda *_:Collection('url','A',[leaf],'tree'))
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:done(fn()))
    app.render_files();node=app.browser.visible_ids[0];app.browser.expand(node)
    app.search_box.set('Hearing');assert len(app.visible)==2
    app.browser.expand(node);assert len(app.visible)==1
    app.browser.expand(node);assert len(app.visible)==2
    app.browser.collapse_all();assert len(app.visible)==1


def test_pasted_channel_playlist_view_and_explicit_video_tab_both_work(app,monkeypatch):
    app.source='youtube'
    monkeypatch.setattr(app,'submit',lambda fn,done,fail=None:done(fn()))
    monkeypatch.setattr(app,'load',lambda url,**kw:REAL_LOAD(app,url,**kw))
    app.mode.set('videos');app.load('https://www.youtube.com/@other/playlists')
    assert app.mode.get()=='playlists' and app.collection.url.endswith('/playlists')
    app.choose_mode('videos')
    assert app.mode.get()=='videos' and app.collection.url.endswith('/videos')
