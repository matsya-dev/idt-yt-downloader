# Release-readiness results — 15 November 2026

**Application source publication: ready. Portable Windows release: held.**

## Completed checks

- **114 tests passed**: the existing 111 application tests plus three new tests
  for source export, privacy checks and exact package-manifest coverage.
- Clean source export uses an explicit file allowlist. It excludes virtual
  environments, Git history, user profiles, test media/logs, old builds, internal
  planning notes and rejected icon concepts. The pattern-based credential and
  personal-path audit found no matches in the exported source.
- Original 2.3.0 ZIP: CRCs and exact manifest coverage passed; no unintended
  profile/media payload found. It was preserved unchanged.
- A separate local review ZIP was built with the corrected notices, approved D3
  icon, clean editable source, privacy note and distribution-status warning.
  All **1,191 file hashes** and ZIP CRCs passed. The manifest covers the exact ZIP
  file set. No local profiles, media or credential-pattern matches were found.
- The extracted review executable passed with a clean PATH from a folder with
  spaces and Telugu characters: native interface, System default, focus-only
  arrows, D3 assets, SQLite, bundled yt-dlp/QuickJS, MP3 128/320 conversion, TLS
  and live Desire Tree metadata access.
- Microsoft Defender reported **no threats** in the original app directory, the
  review ZIP and the review app directory. Scans completed with exit code 0 and
  automatic remediation disabled. Defender antivirus and real-time protection
  were enabled. This is a local scan result, not an assurance of universal trust.
- The exact versions of nine runtime Python packages were checked against PyPI's
  published vulnerability metadata; all returned empty advisory lists. This is
  not a comprehensive audit of Python/Tk, FFmpeg or yt-dlp's embedded dependencies.
- A fixed-date upstream FFmpeg archive was compared against all seven shipped
  DLLs plus FFmpeg/FFprobe; every binary SHA256 matched. Tool fetching now uses
  the recorded archive and per-file hashes instead of selecting new latest tools.
- Version-matched yt-dlp and QuickJS notices, GPLv3/LGPLv3 texts, FFmpeg's root
  license, configuration output, build-source map and PyInstaller exception text
  have been collected. Main upstream source snapshots were archived locally.

The earlier 2.3.0 live checks also covered metadata on all six YouTube channels,
videos/playlists, and downloading/converting/verifying/skipping one short public
test clip. No lecture recordings were downloaded for this readiness pass.

## Remaining release requirements

1. **Corresponding source and complete notices:** FFmpeg's statically linked
   dependencies and yt-dlp's embedded dependencies still need their exact source
   inventory and a complete source-access arrangement. Main-project snapshots and
   generic upstream links alone have not been accepted as sufficient evidence.
   Details and exact commits are in [the licensing review](LICENSING_REVIEW.md).
2. **Other recipient computers:** a browser-downloaded package still needs checks
   on other Windows x64 PCs, including display scaling and first-launch security
   prompts. Local clean-PATH checks do not constitute testing on another computer.
3. **Signing decision:** the application is unsigned. No signing certificate was
   purchased, no signature was applied, and no security setting was disabled.

Publish the clean MIT application source independently. Keep the portable binary
off public release assets until items 1 and 2 are resolved and signing expectations
are documented. The GitHub release can remain a draft during that work.

## Local review package identity

`IDT-YT-Downloader-2.3.0-Local-Review-Windows-x64.zip`

- Size: 106,691,702 bytes.
- SHA256: `3a0f1c2f4e097f2543cbde2e46a72439a4edcc8af6a262565ba915cf78b4c4ae`.

The source ZIP has its own generated `.sha256` file and `source-audit.json` report.
Neither local machine paths nor raw QA logs are included in the public source.
