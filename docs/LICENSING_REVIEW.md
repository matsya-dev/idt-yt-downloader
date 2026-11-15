# Licensing review for 2.4.0

The previous 2.3.0 review identified missing source/notice coverage for the broad
upstream FFmpeg build and official yt-dlp executable. Those binaries are not used
in the 2.4.0 distribution. Their existing local test package remains unchanged.

## Current distribution method

The release provides the portable EXE, a folder ZIP alternative, application source,
and a matching dependency-source ZIP from the same GitHub release page without
charge. Source archives are checksum-verified during packaging. FFmpeg/LAME sources,
all configure/build commands and runtime notices accompany the binary download.
No future written source offer or floating source branch is relied upon.

| Component | Terms | Evidence / distribution handling |
| --- | --- | --- |
| App and icon assets | MIT | Full application source and original notice supplied |
| FFmpeg / FFprobe | LGPL-2.1-or-later | Pinned full source, generated VERSION metadata and complete build script supplied; no C source patches |
| LAME 3.100 | LGPL-2.0-or-later | Full unmodified source and configure/build commands supplied; linked into FFmpeg tools |
| GCC / MinGW runtime portions | GCC runtime exception / MinGW runtime notices | Eligible unmodified GCC compilation; notices supplied; compiler is not shipped |
| yt-dlp 2026.10.26 helper | Unlicense plus its included permissive dependencies | Project-built helper, matching source supplied; optional GPL modules excluded and PYZ inventory checked |
| yt-dlp-ejs 0.8.0 | Unlicense, MIT, ISC | Source distribution includes preferred TypeScript source/lockfile; original library attribution preserved |
| QuickJS-NG v0.18.0 | MIT | Upstream binary hash and full source archive recorded; notice supplied |
| Python 3.12.14 | PSF and included component terms | Exact runtime notices retained; managed CA-rejection policy preserved unchanged |
| Microsoft code in Windows Python | CPython Windows runtime conditions | Version-matched PC/crtlicense.txt retained; one-time agreement; Windows-only; notices and trademarks unmodified |
| Tcl/Tk 8.6.12 | Tcl/Tk permissive terms | Exact version-matched notices supplied |
| OpenSSL / libffi / Expat / zlib / bzip2 / SQLite | Respective upstream terms / public domain | Runtime notices supplied; Python's license includes bzip2 notices |
| Python packages / vendored packages | Respective terms, including MPL-2.0 for certifi | Exact source distributions supplied; notices copied with unique paths so none overwrite another |
| PyInstaller | GPL with bootloader exception; runtime-hook terms | Unmodified bootloader, exception and matching source supplied |

FFmpeg dependency auto-detection, GPL, nonfree and version-3-only code are disabled.
The only external codec library is LAME. PE import checks find only Windows system
DLLs. Statically linked compiler-runtime portions are covered by their notices and
runtime exception. Both FFmpeg and the linked LAME work can be modified and rebuilt
using the complete supplied sources; no runtime hash check prevents replacement.
The app communicates with these tools as separate processes.

The third-party notices remain distinct from the application's MIT terms. Runtime
conditions do not restrict the app's or LGPL components' modification rights.
Manual support updates fetch upstream tools directly; their versions and terms
are separate from this project's initially bundled and redistributed versions.

See [dependency build instructions](DEPENDENCY_BUILD.md), `third-party/sources.json`
and the generated final-release verification report for exact artifact identities.
This is a documented technical redistribution review, not a legal opinion about
all possible uses or jurisdictions. No recordings are included in the release.

Primary references: [FFmpeg](https://ffmpeg.org/legal.html),
[LGPL 2.1](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html),
[CPython Windows runtime conditions](https://github.com/python/cpython/blob/v3.12.14/PC/crtlicense.txt),
[GCC runtime exception](https://www.gnu.org/licenses/gcc-exception-3.1.html),
[PyInstaller exception](https://pyinstaller.org/en/stable/license.html).
