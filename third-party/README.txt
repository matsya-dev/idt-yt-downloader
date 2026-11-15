IDT-YT Downloader — bundled component notices

The application's own source and icon assets use the MIT license in LICENSE.txt.
Third-party components retain their own terms. These terms do not relicense the
whole application. Help > Licenses and source makes the included notices readable.

Matching source and build scripts are supplied beside both Windows downloads:
https://github.com/matsya-dev/idt-yt-downloader/releases/tag/v2.4.0
Download IDT-YT-Downloader-2.4.0-Dependency-Sources.zip. The application's own source
is a separate source asset and the tagged repository. sources.json records exact
upstream versions, source URLs and SHA256 values. No written source offer is used.

FFmpeg / FFprobe:
  Source commit d838f9f9aeb0e09b4d068e2af20a46a12640696f.
  Audio-only project build; LGPL 2.1 or later. See FFmpeg-LGPL-2.1.txt.
  Full unmodified FFmpeg and LAME source and the build commands are supplied.
  External codec library: LAME 3.100, LGPL 2 or later; see LAME-license.txt.
  Automatic dependency discovery, GPL, nonfree and version-3-only options are off.
  The tools are separate processes. Statically linked GCC/MinGW runtime portions
  are covered by the supplied GCC runtime exception and MinGW notices. Windows
  system libraries are provided by Windows. See FFmpeg-build-information.txt.

YouTube helper:
  Project-built yt-dlp 2026.10.26, Unlicense; see yt-dlp-LICENSE.txt.
  yt-dlp-ejs 0.8.0 uses Unlicense plus MIT/ISC library components. Their original
  notices are in Python-packages/yt-dlp-ejs/ and EJS-library-notices.txt.
  Matching yt-dlp/EJS source distributions and build scripts are supplied.
  Optional Mutagen, PyCryptodome, Brotli, WebSockets, curl-cffi and SecretStorage
  modules are not part of this bundled helper.

QuickJS-NG:
  Unmodified upstream Windows release v0.18.0, MIT; QuickJS-LICENSE.txt.
  Matching source is supplied in the dependency source asset.

Python / Tcl / Tk and runtime libraries:
  Python 3.12.14, PSF terms; see Python-license.txt. Its Windows runtime conditions
  are in Python-Windows-CRT-license.txt and are shown once before first use.
  They apply only to Microsoft Distributable Code, not Python or the app's code.
  Microsoft's notices are preserved and this is a Windows-only distribution.
  Tcl/Tk 8.6.12: Tcl-license.txt and Tk-license.txt.
  OpenSSL, libffi, Expat, zlib and bzip2 retain their supplied notices (bzip2's
  notice is also in the Python license). SQLite is public domain.
  Python-package license files, including vendored notices, retain unique paths
  under Python-packages/. Exact source distributions are supplied where recorded.

PyInstaller:
  Unmodified bootloader/runtime hooks; its exception permits bundling this
  independent application. PyInstaller-COPYING.txt and Python-packages/pyinstaller/
  contain the terms and exception. Matching PyInstaller source is supplied.

Manual support updates obtain new tools directly from upstream publishers.
The upstream release and its terms apply to that separately downloaded version.
The source archive above describes the initially bundled versions.

The app is unsigned. No security settings are changed by this software.
