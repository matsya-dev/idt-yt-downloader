"""Read-only public-source smoke checks. Does not download recordings."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vedaboat.model import BVKS_PATH, CHANNELS, TREE_HOME, tree_url, youtube_url
from vedaboat.sources import DesireTree, YouTube
from vedaboat.tools import Tools, run_process


def main():
    root = Path(__file__).resolve().parents[1]
    report = {}
    tree = DesireTree()
    home = tree.browse(TREE_HOME)
    report["desire_tree_root"] = {"folders": len(home.entries), "titles": [e.title for e in home.entries]}
    print("Desire Tree root:", len(home.entries), "folders", flush=True)
    bvks = tree.browse(tree_url(BVKS_PATH))
    report["desire_tree_bvks"] = {"folders": len(bvks.entries)}
    small = next(e for e in bvks.entries if e.title == "Lectures with Hindi Translation")
    recordings = tree.browse(small.url)
    report["desire_tree_files"] = [{"title": e.title, "url": e.url, "size": tree.size(e)} for e in recordings.entries if not e.container]
    print("Desire Tree BVKS:", len(bvks.entries), "folders; file sample:", len(recordings.entries), flush=True)
    tools = Tools(root / "qa" / "live-state", root / "tools")
    youtube = YouTube(tools)
    results = []
    first_video = None
    for title, channel in CHANNELS:
        for mode in ("playlists", "videos"):
            url, kind = youtube_url(channel, mode)
            code, output = run_process(tools.yt_args() + ["--playlist-end", "2", "--flat-playlist", "--skip-download", "--dump-single-json", "--ignore-errors", "--", url], timeout=180)
            info = None
            for line in reversed(output.splitlines()):
                if line.startswith("{"):
                    try:
                        info = json.loads(line)
                        break
                    except ValueError:
                        pass
            result = {"channel": title, "view": mode, "code": code}
            if info:
                collection = youtube.parse(info, url, kind, mode)
                result.update({"title": collection.title, "entries": [{"id": e.video_id or e.collection_id, "title": e.title} for e in collection.entries]})
                if mode == "videos" and collection.entries and first_video is None:
                    first_video = collection.entries[0].url
            else:
                if f'does not have a {mode} tab' in output:
                    result['notice']='No public '+mode+' tab'
                else:
                    result["error"] = output[-2000:]
            results.append(result)
            print(title, mode, "OK" if info or result.get('notice') else "FAILED", flush=True)
    report["youtube"] = results
    if first_video:
        code, output = run_process(tools.yt_args() + ["--no-playlist", "--skip-download", "--dump-single-json", "--", first_video], timeout=180)
        result = {"url": first_video, "code": code}
        try:
            info = next(json.loads(line) for line in output.splitlines() if line.startswith("{"))
            result.update({"title": info.get("title"), "formats": len(info.get("formats", []))})
        except (ValueError, StopIteration):
            result["error"] = output[-3000:]
        report["youtube_format_extraction"] = result
        print("YouTube format extraction:", code, flush=True)
    (root / "qa").mkdir(exist_ok=True)
    (root / "qa" / "live-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
