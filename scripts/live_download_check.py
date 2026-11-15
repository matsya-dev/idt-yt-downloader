"""Small end-to-end network check using a short public clip (no lecture media)."""
import json
import sys
from pathlib import Path
from dataclasses import replace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from vedaboat.engine import Engine
from vedaboat.sources import YouTube
from vedaboat.state import State
from vedaboat.tools import Tools
from vedaboat import __version__


def main():
    root = Path(__file__).resolve().parents[1]
    state = State(root / "qa" / ("download-check-state-"+__version__))
    tools = Tools(state.directory, root / "tools")
    source = YouTube(tools)
    collection = source.browse(sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=jNQXAC9IVRw")
    entry = replace(collection.entries[0],quality=int(sys.argv[2]) if len(sys.argv)>2 else 128)
    destination = root / "qa" / ("test audio "+__version__+" 50% বাংলা")
    state.make_queue([entry], destination)
    engine = Engine(state, tools)
    engine.run()
    report = {"first_run": state.queue()}
    if state.queue()[0]["status"] != "done":
        raise RuntimeError(str(state.queue()))
    output = engine.target_path(entry, destination)
    report["probe"] = tools.probe(output)
    report["bytes"] = output.stat().st_size
    state.make_queue([entry], destination)
    engine.run()
    report["second_run"] = state.queue()
    (root / "qa" / f"download-check-{__version__}-{entry.quality}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Short public clip: downloaded, converted, verified, then skipped")
    state.close()


if __name__ == "__main__":
    main()
