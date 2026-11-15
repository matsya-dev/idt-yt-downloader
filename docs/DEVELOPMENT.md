# IDT-YT Downloader

Portable Windows audio downloader. The native Tk interface follows the approved
two-source, three-step mockup. Sources are public Desire Tree MP3 folders and
YouTube videos, playlists, and channels. All downloads are started manually.

The portable package includes Python/Tk, yt-dlp, bundled EJS scripts, QuickJS-NG,
FFmpeg and FFprobe. Recipients unzip and open `IDT-YT Downloader.exe`.

## Development

Use Windows x64 and Python 3.12+ with Tk. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\fetch_tools.py
.\.venv\Scripts\python.exe run.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\build.py
```

`fetch_tools.py` retrieves standalone releases from yt-dlp, QuickJS-NG, and
FFmpeg-Builds. `tools/versions.json` records URLs, versions and SHA256 hashes.
Runtime updates download to the user's data directory and activate a verified
yt-dlp/QuickJS pair with a single atomic pointer change.

Current build output: `release/IDT-YT-Downloader-2.3.0-Local-Review-Windows-x64.zip`.
Each build uses a fresh timestamped review folder under `dist/`. The ZIP contains the
executable, all runtime dependencies, instructions, licenses, and editable source.
The source copy can use the enclosing package's tools directory by copying it
into its own directory, or running `fetch_tools.py` afresh.

The test suite uses a loopback HTTP server for range, pause and recovery tests,
real bundled FFmpeg/FFprobe for conversion tests, and native Tk for UI tests.
The tests do not download recordings. `scripts/live_check.py` checks public
listings and YouTube format extraction without downloading media.

## Implementation

- `model.py`: source identities, URL validation, Windows-safe path components.
- `sources.py`: direct-child Desire Tree parsing, lazy browsing, YouTube extraction.
- `selection.py`: source-wide selection independent of filters and browsing.
- `state.py`: SQLite WAL state, immutable path assignments and SHA256 file records.
- `engine.py`: bounded concurrent persistent queue, sequential conversion, verified skip/reuse, safe partial
  transfer, exclusive publication, disk checks, download and conversion boundaries.
- `tools.py`: cancellable subprocesses, bundled tool resolution, MP3 verification.
- `updater.py`: staged and verified independent YouTube-support updates.
- `browser.py`: lazy inline hierarchy and Explorer-style keyboard/range selection.
- `layout.py`: compact, resizable three-step layout and icon toolbar.
- `ui.py`: main-thread-only Tk updates delivered from workers through an event queue.
- `shortcuts.py`: editable persisted defaults/custom links with duplicate normalization.
- `breadcrumbs.py`: clickable ancestors and lazy branch menus.
- `theme.py`: shared light/dark palettes for native Tk, ttk, lists, and dialogs.

The app loads only the current collection. Checking a container recursively
discovers its contents. Browsing a channel lists the selected Videos or Playlists
view on demand. Selecting a playlist is a snapshot for that manually started run.

State is `%LOCALAPPDATA%\VedaBoat\vedaboat.sqlite3`; downloaded partials are kept
inside `<destination>/.vedaboat`. App updates replace neither. The optional
`VEDABOAT_DATA_DIR` environment variable isolates development/test state. Only one
app instance per data directory may run at a time.

Desire Tree reuse is scoped to a recording's canonical full site path. Files
already tracked by VedaBoat must match their SHA256. Previously untracked recipient
files at exactly the expected path may be adopted after exact size and audio checks.
No cross-site name matching occurs. Windows-incompatible names are escaped with a
hash; representable original names are kept. YouTube media identity is the video ID;
playlist occurrence identity includes the playlist ID, and stable destination
assignments survive title changes and app updates.

Source code is MIT licensed. Standalone tools remain separate processes under their
own licenses; see `third-party/README.txt` and their bundled notices.

## Version 2.3 behavior

The product is now **IDT-YT Downloader**. The Python module name, Windows profile
directory `%LOCALAPPDATA%/VedaBoat`, `VEDABOAT_DATA_DIR` override, `.vedaboat` work
folders, and shared single-instance mutex remain compatible with older releases.
Renaming never creates an empty profile or moves existing media. New packages and
executables use the new name. The original local 2.3.0 app remains under
`dist/2.3.0/IDT-YT Downloader`; readiness rebuilds use new review folders.

The selected D3 outline-folder SVG lives in `scripts/app_icon.svg`. `make_icon.py`
renders that canonical source to the PNG/ICO assets and generates the toolbar.
Refresh uses a tangent-aligned arrowhead. UI source remains the `vedaboat` package.

Plain arrows move focus without touching ticks or recursively discovering media.
Right only expands and Left only collapses. Shift+Up/Down ticks ranges; Space
toggles the focused item. Explicit Tk Alt bindings replace numeric modifier tests.
Focus is visually distinct and restored through filtering, loading, and collapse.

Clear selection sits next to Select all shown; shown/selected counts share the
right side of that row. Selected totals include hidden entries. Add shortcut is
inside the scrolling list after the last shortcut; sidebar guidance is removed.

System/Light/Dark replaces the old toggle. A new `theme_mode` preference defaults
to System, follows Windows' `AppsUseLightTheme` value read-only, and watches for
changes while open. Explicit overrides persist. No system settings are changed.

## Version 2.2 behavior (historical)

Modern saffron icon and saved dark mode (light default). Settings/Help and folder
actions are text buttons. Guidance is fixed at the bottom of the independently
scrolling shortcuts panel. Editable/removable built-ins include Śrīla Prabhupāda
and Bhakti Vikasa Swami. Restore defaults retains custom links. Channel shortcuts
preserve Videos/Playlists mode. ISKCON Chowpatty/Matajis are virtually under More;
canonical identities and output layouts stay unchanged.

Folders and recordings share selection behavior: Up/Down selects visible rows,
Left/Right collapses/parent or expands/child, Ctrl+arrows keeps checks, Shift extends
ranges, Ctrl+click toggles one item, and clicking a selected item deselects it.
The current collection is tickable; Collapse all preserves checks. Clickable path
branches offer ancestor and sibling navigation. Loading and animated selection
spinners appear inside the list. Cancelled discoveries cannot restore selections.

Network concurrency is 1–10 (default 1), MP3 conversion remains sequential, and
run preferences are snapshotted. Repeat downloads default off; enabled creates
numbered copies. Media locks serialize shared video occurrences; persisted
`run_files` records permit one transfer per recording/quality per run, even across
pause/reopen. State schema 3 retains older queues and rejects newer unknown schemas.

Builds are isolated under `dist/2.2.0/VedaBoat`; older releases remain untouched.
See `Release notes.txt` and `Instructions.txt` for user-facing changes.

## Version 2.1 behavior (historical)

New Desire Tree paths start at `Desire Tree Downloads/<devotee name>/...`.
Source identity still uses the full original site path. Named speaker roots are
recognized independently of navigation. Other collections use the first meaningful
collection folder. Unrelated owners sharing a name receive a stable short suffix.
YouTube uses `YouTube downloads/<channel>/<playlist>/...`, or the channel folder
directly for individual videos. Channel and playlist identities remain stable IDs.

MP3 options are 96, 128 (default), 192, 256, and 320 kbps. Queue entries snapshot
quality, so preferences changed later never alter a resumed conversion. Verification
identity and filenames distinguish quality; a 128 kbps file cannot satisfy a 320 kbps
request. Bitrate is checked with FFprobe after encoding. Older queues without these
fields default to 128 kbps and retain their 2.0 paths. Old files are not moved/deleted;
verified local recordings can be reused in the new hierarchy.

The browser shows native expansion arrows. Expanding loads only that container.
Mouse and keyboard row selection checks recordings; highlighting a folder does
not crawl it until its checkbox or Space is used. Search preserves checked items
outside the visible list. Window geometry, columns, and sidebar divider are saved.
The approved app icon is P: a saffron-and-cream pixel sailboat with a download arrow.

Builds are isolated under `dist/2.1.0/VedaBoat`; older releases remain untouched.
