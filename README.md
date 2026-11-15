# IDT-YT Downloader

A simple Windows audio downloader for public Desire Tree recordings and YouTube
videos, playlists and channels. Downloads are started manually.

## Release status

The application source is available under the MIT license. The portable Windows
package is undergoing release review and is **not yet cleared for public
redistribution**. Its bundled tools need a complete corresponding-source and
third-party notice review. See [the licensing review](docs/LICENSING_REVIEW.md)
and [release-readiness results](docs/RELEASE_READINESS.md).

The local 2.3.0 test build passed 111 application tests, native Windows keyboard
and theme checks, a live short-clip download/conversion/skip check, and extraction
with a clean PATH. This does not replace the remaining licensing or recipient-PC
checks. Additional release-audit checks are described in the release report.

## What it does

- Browse Desire Tree folders and select individual MP3s or whole folder trees.
- Browse Videos and Playlists on six built-in YouTube channels or paste another
  public video, playlist or channel link.
- Keep editable shortcuts and selections while searching.
- Choose MP3 quality: 96, 128 (default), 192, 256 or 320 kbps.
- Pause and resume unfinished work; verify and skip existing recordings.
- Save repeat downloads as numbered copies when enabled.
- Follow the Windows theme by default, with Light and Dark options.

Desire Tree downloads start under `Desire Tree Downloads/<devotee>/...`.
YouTube downloads use `YouTube downloads/<channel>/<playlist>/...`.

Use only recordings you are permitted to download and follow the source site's
terms. This independent project is not affiliated with or endorsed by YouTube,
Google, ISKCON Desire Tree, or the listed channels.

## Development

Use Windows x64 with Python 3.12+ and Tk:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts\fetch_tools.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe run.py
```

The fetch script uses the exact URLs and SHA256 hashes in `tools/versions.json`.
It fails if an upstream archive no longer matches; it does not silently upgrade
build dependencies. Upstream daily assets may expire and then require a reviewed
manifest update. Runtime YouTube-support updates remain a separate manual action.

`python scripts/release_audit.py` creates a clean source ZIP and an audit report.
`python scripts/build.py` creates a **local review package**, not a cleared public
release. Follow [the release checklist](docs/RELEASE_CHECKLIST.md) before publishing
binaries. See [development details](docs/DEVELOPMENT.md) and
[contributing](CONTRIBUTING.md).

## Help and privacy

Read [Instructions.txt](Instructions.txt) for the interface and keyboard controls.
Report problems in [GitHub Issues](https://github.com/matsya-dev/idt-yt-downloader/issues)
with the app version, Windows version and steps to reproduce. Remove personal
paths or private links from screenshots and error details.

Preferences and queues remain under `%LOCALAPPDATA%\VedaBoat` for compatibility
with the former app name. [Privacy details](PRIVACY.md).

## Licenses

The app's own code and included icon assets use the [MIT license](LICENSE.txt).
The standalone tools and runtime dependencies retain their own licenses. The MIT
license does not relicense FFmpeg, yt-dlp's bundled components, or other third-party
code. See [third-party notices](third-party/README.txt) and
[the redistribution review](docs/LICENSING_REVIEW.md).
