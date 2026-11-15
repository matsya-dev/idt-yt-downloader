# Redistribution review — 15 November 2026

This is a technical inventory and release decision, not a legal opinion.

## Release decision

**Application source:** suitable for publication under the existing MIT license,
with the included notices. The clean source export contains no standalone tools,
user profile, downloaded recordings, test outputs or old release packages.

**Portable Windows binary:** do not publish yet. The exact main source commits
and build recipe references have been identified, but complete corresponding
source access and notices for bundled/transitive dependencies remain unverified.
The 2.3.0 ZIP remains a local test build.

## Reviewed components

| Component | License and evidence | Status |
| --- | --- | --- |
| Application Python code, tests and icon assets | Existing MIT license; source supplied | Ready for source publication |
| Python/Tcl/Tk and Python packages | Runtime and package notices copied by builder; pinned installed versions recorded in dependency inventory | Notices inventoried; inspect final archive after rebuilding |
| FFmpeg/FFprobe and av* DLLs | Binary `-L` reports LGPLv3-or-later; `--enable-version3`, shared DLLs, no `--enable-gpl` or `--enable-nonfree` | Main source identified; transitive source/notice review incomplete |
| yt-dlp 2026.10.26 standalone executable | yt-dlp source is Unlicense; executable includes components with other licenses, including GPL | Tag-matched notices saved; complete executable dependency source inventory incomplete |
| QuickJS-NG v0.18.0 | MIT; tag-matched notice saved | Main source identified |
| PyInstaller | GPL with bootloader exception permits bundling independent application code | Record/copy exception text with binary notices |

## FFmpeg evidence

Bundled version: `n9.0.2-57-gd838f9f9ae-20261114`.

- FFmpeg source commit:
  [`d838f9f9aeb0e09b4d068e2af20a46a12640696f`](https://github.com/FFmpeg/FFmpeg/tree/d838f9f9aeb0e09b4d068e2af20a46a12640696f)
- FFmpeg-Builds recipes commit, resolved from the original release tag:
  [`c9fe5114060e507409f7ee07edfd82efaf25d767`](https://github.com/FFmpeg-Builds/FFmpeg-Builds/tree/c9fe5114060e507409f7ee07edfd82efaf25d767)
- Original upstream ZIP SHA256:
  `4bd4716920debc7b070a21e3fe005f2cfa6562eb1975fc4f185eaed233ad3e4e`.
- Individual binary hashes remain in `tools/versions.json`.
- `third-party/FFmpeg-source-map.json` lists upstream recipe source references.
  It deliberately includes disabled and platform-only recipes; it is not a
  certified list of libraries present in the Windows binary.
- FFmpeg's complete version/configuration output is in
  `third-party/FFmpeg-build-information.txt`.

The previous notice's general reference to the floating `release/9.0` branch was
insufficient to identify the exact source. It has been replaced by immutable
references. The original fetch script also looked for license files only under
`doc/`, while this upstream archive places `LICENSE.txt` at its root; the fetch
and packaging preparation now account for that root notice.

## Work required before a public binary release

1. Enumerate the libraries actually built into the shipped FFmpeg DLLs, including
   static dependencies, patches, Rust crates/submodules and their required notices.
   Match them to the source revisions and build instructions used by this binary.
2. Provide complete corresponding source access for the LGPL/GPL components in
   the manner permitted by their licenses, clearly linked beside the Windows
   download. An FFmpeg-only tarball plus a build-script archive does not by itself
   establish completeness for all linked libraries.
3. Do the same for the third-party components inside the yt-dlp standalone EXE.
   Its project source archive alone is not the full executable's source inventory.
4. Include both GPLv3 and LGPLv3 texts and all component notices in the final
   package. Main app MIT terms must not be described as covering the whole bundle.
5. Verify the final source-access links and their continued availability before
   publishing. Do not rely on the rolling `latest` binary release for provenance.

Exact top-level source snapshots have been saved locally for the review. They are
supplemental evidence and are not labelled a complete corresponding-source bundle.
An upstream-provided complete source bundle, or a smaller documented/rebuildable
tool build, could resolve the remaining tool-specific work.

## References

- [FFmpeg license and redistribution checklist](https://ffmpeg.org/legal.html)
- [LGPLv3 terms](https://www.gnu.org/licenses/lgpl-3.0.html)
- [GPLv3 terms, including section 6](https://www.gnu.org/licenses/gpl-3.0.html)
- [yt-dlp version-matched bundled license notices](https://github.com/yt-dlp/yt-dlp/blob/2026.10.26/THIRD_PARTY_LICENSES.txt)
- [PyInstaller license and bootloader exception](https://pyinstaller.org/en/stable/license.html)
