# IDT-YT Downloader

A simple Windows audio downloader for public Desire Tree recordings and YouTube
videos, playlists and channels. Downloads are started manually.

## Download

[Open the latest release](https://github.com/matsya-dev/idt-yt-downloader/releases/latest).

- **Portable EXE:** download `IDT-YT-Downloader-2.4.1-Windows-x64.exe` and double-click.
  No installation, separate Python or manual unzipping is needed. Bundled resources
  unpack automatically while the app runs.
- **ZIP alternative:** extract the complete ZIP and open `IDT-YT Downloader.exe`.
  Keep the extracted folder together.

Windows x64 is supported. The app is unsigned, so Windows may display an
unrecognized-app warning. Verify the official source and published checksum.
The Windows Python runtime conditions are shown once before first use; the app
and other components keep their own licenses. Read [Instructions.txt](Instructions.txt).

## Features

- Browse Desire Tree folders and select individual MP3s or whole folder trees.
- Browse Videos and Playlists on six built-in YouTube channels, or paste another
  public video, playlist or channel link.
- Editable shortcuts, title search and selection that persists through filtering.
- MP3 quality choices: 96, 128 (default), 192, 256 and 320 kbps.
- Pause/resume, saved unfinished work and verified existing-file skipping.
- Optional numbered repeat copies and 1–10 simultaneous downloads (default 1).
- System theme by default, with Light and Dark overrides.

Desire Tree downloads use `Desire Tree Downloads/<devotee>/...`.
YouTube downloads use `YouTube downloads/<channel>/<playlist>/...`.
Use recordings you are permitted to download and follow the source site's terms.
This independent project is not affiliated with or endorsed by YouTube, Google,
Microsoft, ISKCON Desire Tree or the listed channels.

## Updates and privacy

Replace the portable EXE, or extract a ZIP update into a new folder. Preferences,
shortcuts and queues remain under `%LOCALAPPDATA%\VedaBoat` for compatibility with
the former app name. Downloaded files and `.vedaboat` partial folders stay in the
chosen destination. Close older versions before opening the update.

[Privacy](PRIVACY.md) · [Report a problem](https://github.com/matsya-dev/idt-yt-downloader/issues)

## Source and development

The release includes application source, a matching dependency-source archive,
checksums and verification results. See [licensing review](docs/LICENSING_REVIEW.md)
and [dependency build instructions](docs/DEPENDENCY_BUILD.md).

Use Windows x64 and Python 3.12 with Tk:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts\fetch_tools.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe run.py
```

The tool fetch script uses the recorded final release and per-file hashes.
To rebuild the audio tools from source, follow the dependency build guide.
`python scripts/build.py` creates both portable formats and source assets.
`python scripts/verify_portable.py --network` tests both artifacts with a clean
PATH, including a renamed standalone EXE in a folder containing no sidecar files.
See [contributing](CONTRIBUTING.md) and [the release checklist](docs/RELEASE_CHECKLIST.md).

The app's own code and icons use the [MIT license](LICENSE.txt). Runtime and tool
components retain their separate terms; see [third-party notices](third-party/README.txt).
