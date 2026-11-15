# Release readiness — 2.4.0

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

The staged candidates are tested on a clean GitHub Windows runner before release
publication. The final release verification report records that run, its exact
asset hashes, test totals and OS. Local raw QA files and profiles are not uploaded.

The application is unsigned. Antivirus results do not guarantee SmartScreen
reputation or that every security product will allow a first launch. Human beta
feedback on additional Windows laptops is useful after release; no such human
trial is claimed by these automated checks.
