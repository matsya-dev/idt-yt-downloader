IDT-YT Downloader third-party components

The application's own source and icon assets are MIT licensed. Standalone tools
and runtime libraries keep their own licenses; MIT does not cover the whole
portable bundle. The app invokes FFmpeg, FFprobe, yt-dlp and QuickJS as separate
processes. The FFmpeg tools load replaceable shared av* DLLs from tools/.

PUBLIC BINARY RELEASE STATUS: HOLD
Exact main source references and notices have been collected. Complete source
access and required notices for transitive FFmpeg and yt-dlp executable components
are not yet verified. See docs/LICENSING_REVIEW.md (source/docs/ in a local package).
Do not label the main-project source snapshots a complete source bundle.

FFmpeg / FFprobe / av* DLLs:
  Actual binary version: n9.0.2-57-gd838f9f9ae-20261114.
  Actual binary -L result: LGPL version 3 or later.
  FFmpeg-LICENSE.txt is copied from the upstream binary archive root.
  GPL-3.0.txt and LGPL-3.0.txt contain the governing base/supplemental texts.
  Source: https://github.com/FFmpeg/FFmpeg/tree/d838f9f9aeb0e09b4d068e2af20a46a12640696f
  Recipes: https://github.com/FFmpeg-Builds/FFmpeg-Builds/tree/c9fe5114060e507409f7ee07edfd82efaf25d767
  See FFmpeg-build-information.txt, FFmpeg-source-map.json and tools/versions.json.
  Recipe references include disabled/platform-only packages; they do not establish
  which dependencies were actually linked or that all corresponding source is supplied.

yt-dlp 2026.10.26:
  Main source: Unlicense. The standalone EXE contains additional licensed components,
  including GPL components. Tag-matched notices: yt-dlp-LICENSE.txt and
  yt-dlp-THIRD_PARTY_LICENSES.txt. Main source (not the full executable source):
  https://github.com/yt-dlp/yt-dlp/tree/2026.10.26

QuickJS-NG v0.18.0:
  MIT; tag-matched notice: QuickJS-LICENSE.txt.
  Source: https://github.com/quickjs-ng/quickjs/tree/v0.18.0

Python / Tcl / Tk / Python packages:
  Exact package versions and project references: Python-package-inventory.json.
  The builder copies Python/Tcl/Tk notices and installed-package LICENSE/NOTICE
  files beside this file. Python: https://www.python.org/psf/license/
  Tcl/Tk: https://www.tcl.tk/software/tcltk/license.html

PyInstaller:
  GPL with bootloader exception; see PyInstaller-COPYING.txt.
  https://pyinstaller.org/en/stable/license.html

No application files have been code-signed by this project. A clean antivirus
result is separate from signing and license compliance.
