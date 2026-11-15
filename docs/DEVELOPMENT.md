# Development notes

Use Windows x64 with Python 3.12 and Tk. `requirements-lock.txt` records the
release's complete development environment. `requirements.txt` remains the small
runtime requirement list. Tool versions/hashes are in `tools/versions.json`.

The default developer path fetches exactly the published tools via
`scripts/fetch_tools.py`. Rebuilding dependencies uses the separate procedure in
[DEPENDENCY_BUILD.md](DEPENDENCY_BUILD.md). `scripts/build.py` builds a standalone
EXE and folder ZIP in new timestamped directories, preserving older packages.

Resource discovery supports PyInstaller's one-file extraction directory, its new
folder-bundle layout, and older sidecar layouts. Preferences, agreement state,
shortcuts, completion records and queued work remain outside the extracted app,
under `%LOCALAPPDATA%\VedaBoat`. The historical Python module name `vedaboat`,
`VEDABOAT_DATA_DIR` override, `.vedaboat` partial folders and shared per-profile
mutex remain intentionally compatible with older versions.

Modules:

- `model.py`: canonical source identities and Windows-safe destination components.
- `sources.py`: direct-child Desire Tree parsing and lazy YouTube extraction.
- `selection.py` / `browser.py`: persistent ticks, focus-only arrows and ranges.
- `state.py`: SQLite WAL, stable path assignments and verified file hashes.
- `engine.py`: bounded concurrent queue, safe partial transfer/conversion and reuse.
- `tools.py` / `updater.py`: bundled-tool discovery and atomic support updates.
- `layout.py` / `ui.py`: resizable native interface and main-thread event handling.
- `theme.py`: System/Light/Dark palettes and Windows theme detection.
- `license_notice.py`: one-time Windows runtime agreement, keyed to the exact text.
- `diagnostics.py`: isolated frozen-runtime, codec, interface and TLS checks.

The tests use local HTTP fixtures, generated audio and temporary profiles. They
cover resume, collisions, Unicode/long paths, quality, concurrency, migration,
keyboard selection and themes. Live scripts are separate and deliberately invoked.
`verify_portable.py` tests the actual EXE alone in a renamed Unicode path, relaunch,
and exact ZIP hash coverage with only Windows system directories on PATH.

The GitHub Windows verification job downloads the exact staged release assets,
checks their hashes/source manifests, runs the application suite and repeats the
portable-artifact checks on a clean hosted runner. Final reports distinguish that
Windows Server environment from local Windows 11 and human beta feedback.
