# Matching dependency source and build instructions

The release's `IDT-YT-Downloader-2.4.0-Dependency-Sources.zip` provides the unmodified
source archives, hashes, required notices and build scripts used for the bundled
audio tools. The application's own complete source is a separate release asset
and is also in the tagged GitHub repository. Source access is provided beside
both Windows download formats without charge.

## Audio-tool scope

FFmpeg is built from commit `d838f9f9aeb0e09b4d068e2af20a46a12640696f`, with one
external codec library: unmodified LAME 3.100. `--disable-autodetect` prevents
unrecorded external libraries from being found on the build computer. GPL,
nonfree and version-3-only options are disabled. Video encoders/decoders and
hardware acceleration are not part of this audio-only build. AAC, Opus, Vorbis,
MP3, FLAC, ALAC and common PCM audio are enabled, together with the container and
remuxing support needed by YouTube audio downloads. HTTPS uses Windows Schannel.

FFmpeg and LAME are statically linked into the tools. The app invokes those
tools as separate processes. Both complete sources and all build commands are
supplied so the tools can be modified and rebuilt. The app does not validate a
user-replaced FFmpeg binary against the distribution hash at runtime. Source
publication, rather than a written source offer, is the distribution method.

The compiler's standard runtime components use the GCC Runtime Library Exception
and MinGW runtime terms. Their notices are included. The compiler is a development
tool, is not shipped inside the app, and can be downloaded from the pinned w64devkit
release recorded in `third-party/sources.json`.

## Rebuild on Windows x64

Use Python 3.12 with Tk. From the application source directory:

To use the supplied source archives instead of fetching them again, first copy
the dependency ZIP's `.tar.gz` files into `vendor/dependency-sources/`. Its
`sources.json` supplies their expected hashes. Use the application-source asset
as the build root; the dependency asset's scripts are an additional copy.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts\prepare_dependencies.py
& 'vendor\portable-tools\w64devkit\bin\sh.exe' scripts/build_audio_tools.sh
.\.venv\Scripts\python.exe scripts\build_youtube_tool.py
```

`prepare_dependencies.py` verifies and extracts the original FFmpeg and LAME
archives and verifies the development compiler download. The shell script writes
only generated FFmpeg `VERSION` metadata; it does not patch upstream C sources.
All configure/compiler switches are in the script. Output tools are under
`vendor/portable-tools/output`. No system-wide compiler installation is required.

The yt-dlp helper uses yt-dlp 2026.10.26 and yt-dlp-ejs 0.8.0, with the Python
runtime and the recorded requests dependencies. Optional Mutagen, PyCryptodome,
Brotli, WebSockets, curl-cffi and SecretStorage packages are excluded. The bundled
EJS library preserves MIT/ISC third-party attribution; its preferred TypeScript
source and lockfile are in the supplied EJS source distribution. QuickJS-NG is
the unmodified v0.18.0 upstream Windows tool under its MIT license, with matching
source supplied.

PyInstaller's unmodified bootloader/runtime hooks are covered by its bundled
license and exception. Matching PyInstaller source is supplied. Python and its
runtime dependencies keep their own notices. The existing managed Python build
uses an additional bundled CA-rejection policy; it is retained unchanged rather
than weakening TLS verification. Normal Python installations do not require that
additional policy file.

Rebuilding on another machine may change executable timestamps and Python runtime
versions, so this is a source-rebuild procedure, not a claim of byte-identical
reproducible binaries. The published hashes identify the actual tested artifacts.

Manual YouTube-support updates download new upstream tools directly from their
publishers. Their own releases and licenses apply to those separately obtained
versions; the project's source archive describes the initially bundled versions.
