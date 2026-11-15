from dataclasses import replace
import json
from pathlib import Path
import wave

import pytest

from vedaboat.engine import Engine
from vedaboat.model import BVKS_PATH, Entry, devotee_layout, audio_quality
from vedaboat.sources import YouTube
from vedaboat.state import State
from vedaboat.tools import Tools


def video(**kw):
    args=dict(key="youtube:abcdefghijk",source="youtube",kind="video",title="ভক্তি",url="url",video_id="abcdefghijk",channel_id="UCone",channel_title="Channel One",duration=60)
    args.update(kw)
    return Entry(**args)


def test_desire_tree_starts_at_devotee_beneath_requested_parent(tmp_path):
    state=State(tmp_path/'state');engine=Engine(state,None)
    entry=Entry('tree:'+BVKS_PATH+'/English/talk.mp3','tree','audio','talk','url',path=BVKS_PATH+'/English/talk.mp3')
    assert engine.relative_path(entry)==Path('Desire Tree Downloads')/'His_Holiness_Bhakti_Vikas_Swami'/'English'/'talk.mp3'
    state.close()


def test_prabhupada_and_nonstandard_collections_have_safe_roots():
    owner,name,tail=devotee_layout('/01_-_Srila_Prabhupada/Lectures/1970/a.mp3')
    assert name=='Srila_Prabhupada' and tail==Path('Lectures/1970/a.mp3')
    owner,name,tail=devotee_layout('/06_-_More/Kirtans/India/a.mp3')
    assert name=='Kirtans' and tail==Path('India/a.mp3')


def test_youtube_channels_and_playlists_have_readable_folders(tmp_path):
    state=State(tmp_path/'state');engine=Engine(state,None)
    standalone=engine.relative_path(video())
    assert standalone.parent==Path('YouTube downloads')/'Channel One'
    playlist=engine.relative_path(video(collection_id='PLone',collection_title='Śrīmad Bhāgavatam',index=12))
    assert playlist.parent==standalone.parent/'Śrīmad Bhāgavatam'
    assert playlist.name.startswith('0012 - ')
    state.close()


def test_same_named_unrelated_channels_are_not_merged(tmp_path):
    state=State(tmp_path/'state');engine=Engine(state,None)
    first=engine.relative_path(video())
    second=engine.relative_path(video(channel_id='UCtwo'))
    assert first.parent!=second.parent
    state.close()


def test_different_quality_has_different_verification_and_filename(tmp_path):
    state=State(tmp_path/'state');engine=Engine(state,None)
    root=tmp_path/'downloads';root.mkdir()
    entry=video();old=root/'old-128.mp3';old.write_bytes(b'old128')
    state.remember_file(entry.artifact_id,old)
    high=replace(entry,quality=320)
    assert high.artifact_id!=entry.artifact_id
    assert not engine.existing(high,root,engine.target_path(high,root))
    assert '[320kbps]' in engine.target_path(high,root).name
    assert high.estimated_size==2400000 and entry.estimated_size==960000
    assert old.read_bytes()==b'old128'
    state.close()


def test_queue_quality_and_layout_survive_reopening_and_setting_change(tmp_path):
    state=State(tmp_path/'state')
    state.make_queue([video(quality=192)],tmp_path/'downloads')
    state.put('youtube_quality',320);state.close()
    state=State(tmp_path/'state');entry=Entry.from_dict(json.loads(state.queue()[0]['entry']))
    assert entry.quality==192 and entry.layout_version==2
    assert state.get('youtube_quality')==320
    state.close()


def test_legacy_queue_keeps_128_and_its_existing_path(tmp_path):
    raw=video().to_dict();raw.pop('quality');raw.pop('layout_version')
    old=Entry.from_dict(raw)
    assert old.quality==128 and old.layout_version==1
    state=State(tmp_path/'state');engine=Engine(state,None)
    assert engine.relative_path(old).parent==Path('YouTube/Videos')
    state.close()


def test_verified_old_download_is_reused_without_moving_it(tmp_path):
    state=State(tmp_path/'state');engine=Engine(state,None)
    root=tmp_path/'downloads';root.mkdir();entry=video()
    old=root/'YouTube'/'Videos'/'old.mp3';old.parent.mkdir(parents=True);old.write_bytes(b'old-verified')
    state.remember_file(entry.artifact_id,old)
    new=engine.target_path(entry,root)
    assert engine.existing(entry,root,new)
    assert old.read_bytes()==new.read_bytes()==b'old-verified'
    state.close()


@pytest.mark.parametrize('quality',[96,128,192,256,320])
def test_every_quality_is_verified_at_requested_bitrate(tmp_path,quality):
    tools=Tools(tmp_path/'state',Path(__file__).resolve().parents[1]/'tools')
    source=tmp_path/'input.wav';target=tmp_path/f'{quality}.mp3'
    with wave.open(str(source),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(22050);out.writeframes(b'\0\0'*22050)
    tools.convert(source,target,1,quality)
    assert int(tools.probe(target)['streams'][0]['bit_rate'])==quality*1000


def test_unknown_quality_falls_back_to_128():
    assert audio_quality('bad')==audio_quality(999)==128


def test_old_saved_state_is_upgraded_without_losing_queue(tmp_path):
    state=State(tmp_path/'state');state.make_queue([video()],tmp_path/'downloads')
    raw=video().to_dict();raw.pop('quality');raw.pop('layout_version')
    with state.db:
        state.db.execute('UPDATE queue SET entry=?',(json.dumps(raw),))
        state.db.execute('PRAGMA user_version=1')
    state.close()
    state=State(tmp_path/'state')
    assert state.db.execute('PRAGMA user_version').fetchone()[0]==3
    entry=Entry.from_dict(json.loads(state.queue()[0]['entry']))
    assert entry.quality==128 and entry.layout_version==1
    state.close()
