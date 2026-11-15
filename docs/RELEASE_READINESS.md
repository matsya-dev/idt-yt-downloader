# Release readiness — 2.4.1

The patch fixes reselecting a child folder after unticking its parent. A live,
listing-only UI check reproduced the 2.4.0 failure for Bhakti Vikasa Swami's
English lectures / Bhagavad Gita / Chapter-01 (zero selected) and verified that
the patched app selects all 18 files. A Prabhupada Japa comparison selected both
files after the same parent-exclusion sequence. No lecture audio was downloaded.

The full suite passes 125 tests, including folder/playlist exclusions, ordinary
and Ctrl+click reselection, and the revised compact layout on both source tabs.
Clear selection and counts are below the list, with Select all shown beside the
Collapse all icon above it. The frozen app's interface diagnostic also checks
folder reselection. Native inspection confirmed the footer placement.

Both final portable formats pass isolated launch, relaunch, codec, resource and
TLS checks. All 1,111 ZIP file hashes match. Defender reports no threats in the
final EXE or ZIP. The tool binaries and dependency licenses are unchanged from
2.4.0; matching sources and notices are included again.

Clean Windows verification of the staged 2.4.1 candidates is pending. Publication
must wait for it and restoration of temporary workflow access to read-only.

## Previous 2.4.0 release evidence

Local checks passed for the single portable EXE and ZIP alternative, including
standalone renamed launch, relaunch, native interface, all codec diagnostic
formats, System theme, D3 resources, TLS and exact ZIP hash coverage. The full
application suite passed 119 tests. Microsoft Defender found no threats in the
final EXE or ZIP. Live Desire Tree and all six YouTube channel views passed, as
did a short test-clip download/conversion/verified-skip run.

The earlier 2.3.0 dependency-source gaps were resolved by rebuilding FFmpeg/LAME
and yt-dlp from a small pinned source set. The release provides exact matching
sources, build scripts, notices and checksums beside both binary formats. The
Windows Python runtime conditions are shown once and remain limited to those
Microsoft components. See [the licensing review](LICENSING_REVIEW.md).

The exact staged files also passed on a clean GitHub Windows Server 2025 runner: 119 tests, zero failures, errors or skips, plus standalone EXE launch/relaunch and ZIP checks. All 1,109 ZIP file hashes and 77 dependency-source/notice hashes matched.

[Successful clean Windows run](https://github.com/matsya-dev/idt-yt-downloader/actions/runs/43721675497). The test driver used Python 3.12.10; the portable app supplies its own Python 3.12.14 runtime and needed no installed Python or audio tools on PATH.

Temporary workflow write access was explicitly approved for draft-asset verification and restored to read-only after the job completed. The final release verification report records the tested files, hashes and environments. Local raw QA files and profiles are not uploaded.

The application is unsigned. Antivirus results do not guarantee SmartScreen
reputation or that every security product will allow a first launch. Human beta
feedback on additional Windows laptops is useful after release; no such human
trial is claimed by these automated checks.
