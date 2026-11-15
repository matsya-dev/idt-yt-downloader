from vedaboat.model import TREE_HOME, tree_url
from vedaboat.shortcuts import Shortcuts, defaults, normalize_link
from vedaboat.sources import DesireTree
from vedaboat.state import State


def test_edit_remove_and_restore_defaults_persist_without_losing_custom(tmp_path):
    state=State(tmp_path/'state');book=Shortcuts(state)
    assert len([i for i in book.items if i['source']=='youtube'])==6
    assert any(i['name']=='Śrīla Prabhupāda' for i in book.items)
    bvks=next(i for i in book.items if i['id']=='default:bvks')
    assert bvks['name']=='Bhakti Vikasa Swami'
    book.put('My lectures',bvks['url'],bvks['id']);book.remove('default:prabhupada')
    custom=book.put('Other playlists','https://www.youtube.com/@another/playlists')
    state.close();state=State(tmp_path/'state');book=Shortcuts(state)
    assert not any(i['id']=='default:prabhupada' for i in book.items)
    assert next(i for i in book.items if i['id']=='default:bvks')['name']=='My lectures'
    assert next(i for i in book.items if i['id']==custom['id'])['mode']=='playlists'
    book.restore()
    assert any(i['name']=='Śrīla Prabhupāda' for i in book.items)
    assert custom in book.items
    state.close()


def test_shortcuts_normalize_equivalent_links_and_reject_duplicates(tmp_path):
    import pytest
    from vedaboat.model import UserError
    state=State(tmp_path/'state');book=Shortcuts(state)
    book.put('Video','https://youtu.be/abcdefghijk?feature=share')
    with pytest.raises(UserError,match='already'):
        book.put('Same','https://www.youtube.com/watch?v=abcdefghijk')
    assert normalize_link('https://www.youtube.com/@someone/playlists')[2]=='playlists'
    assert normalize_link('https://audio.iskcondesiretree.com/index.php?f=/one&q=f')[1]==tree_url('/one')
    state.close()


def test_virtual_more_preserves_original_urls_and_browsing_identity():
    source=DesireTree()
    html=''.join(f'<a href="{tree_url(p)}">{name}</a>' for p,name in [
        ('/04_-_ISKCON_Matajis','ISKCON Matajis'),('/05_-_ISKCON_Chowpatty','ISKCON Chowpatty'),('/06_-_More','More')])
    assert [e.title for e in source.parse(html,'/').entries]==['More']
    more=source.parse('<html></html>','/06_-_More')
    assert {e.path for e in more.entries}=={'/04_-_ISKCON_Matajis','/05_-_ISKCON_Chowpatty'}
    assert all(e.key=='tree:'+e.path and e.url==tree_url(e.path) for e in more.entries)
    assert source.parse('<html></html>','/04_-_ISKCON_Matajis').parent_url==more.url


def test_run_preferences_are_snapshotted_and_waiting_conversion_recovers(tmp_path):
    from vedaboat.model import Entry
    state=State(tmp_path/'state')
    e=Entry('one','tree','audio','One','url',path='/one.mp3')
    state.put('concurrency',10);state.put('repeat_downloads',True)
    state.make_queue([e],tmp_path/'downloads');state.job_status(0,'waiting_conversion')
    state.put('concurrency',1);state.put('repeat_downloads',False);state.close()
    state=State(tmp_path/'state')
    assert state.get('queue_options')=={'concurrency':10,'repeat':True}
    assert state.queue()[0]['status']=='pending'
    state.close()
