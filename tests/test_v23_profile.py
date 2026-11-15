"""The rebrand must continue the same saved profile and unfinished work."""
from pathlib import Path
from vedaboat.model import Entry
from vedaboat.shortcuts import Shortcuts
from vedaboat.state import State, data_directory


def test_renamed_app_keeps_existing_profile_and_all_download_records(tmp_path,monkeypatch):
    monkeypatch.delenv('VEDABOAT_DATA_DIR',raising=False)
    monkeypatch.setenv('LOCALAPPDATA',str(tmp_path))
    profile=tmp_path/'VedaBoat'
    assert data_directory()==profile
    destination=tmp_path/'My audio తెలుగు';destination.mkdir()
    partial=destination/'.vedaboat'/'partials'/'retained.part'
    partial.parent.mkdir(parents=True);partial.write_bytes(b'unfinished original audio')
    completed=destination/'completed.mp3';completed.write_bytes(b'verified original audio')
    state=State(profile)
    state.put('destination',str(destination));state.put('dark_mode',True)
    state.put('tree_url','https://audio.iskcondesiretree.com/index.php?q=f&f=/existing')
    book=Shortcuts(state);book.remove('default:prabhupada')
    custom=book.put('My playlist','https://www.youtube.com/playlist?list=PLretained')
    e=Entry('tree:/speaker/one.mp3','tree','audio','One','url',path='/speaker/one.mp3')
    second=Entry('youtube:abcdefghijk','youtube','video','Two','url',video_id='abcdefghijk',quality=192)
    state.make_queue([e,second],destination,concurrency=4,repeat=True)
    state.job_status(0,'done');state.job_status(1,'converting')
    state.remember_file(e.artifact_id,completed)
    state.fixed_path('retained-path','original/subfolder/original.mp3')
    state.close()
    reopened=State(data_directory())
    try:
        assert [r['status'] for r in reopened.queue()]==['done','pending']
        assert reopened.get('destination')==str(destination)
        assert reopened.get('queue_options')=={'concurrency':4,'repeat':True}
        assert reopened.verified_file(e.artifact_id,destination)==completed
        assert reopened.fixed_path('retained-path','new/proposal.mp3')=='original/subfolder/original.mp3'
        assert custom in Shortcuts(reopened).items
        assert not any(i['id']=='default:prabhupada' for i in Shortcuts(reopened).items)
        assert partial.read_bytes()==b'unfinished original audio'
        assert reopened.get('tree_url').endswith('/existing')
        assert not (tmp_path/'IDT-YT Downloader').exists()
    finally:reopened.close()
