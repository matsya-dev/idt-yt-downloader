# Release checklist

1. Freeze runtime/build versions and source URLs. Keep existing user state and
   older releases intact. Do not include profiles, recordings, test outputs,
   credentials or obsolete design alternatives in public artifacts.
2. Build the recorded audio-only FFmpeg/LAME and minimal yt-dlp helper, or fetch
   the exact previously tested tools. Verify hashes, license notices and source
   completeness. See LICENSING_REVIEW.md and DEPENDENCY_BUILD.md.
3. Run the complete Windows test suite and source/runtime diagnostics.
4. Run scripts/build.py to create the portable EXE, folder ZIP, application-source
   ZIP, dependency-source ZIP and SHA256SUMS. Both source assets must be available
   with the Windows downloads, without charge.
5. Run scripts/verify_portable.py --network. Verify the renamed EXE runs by itself
   with a clean PATH, relaunch it, and verify every ZIP manifest member. Check all
   audio diagnostic formats and the in-app license viewer.
6. Scan the final EXE, ZIP and extracted folder using Microsoft Defender. Preserve
   scan results and exit codes. Do not disable system protection to pass a check.
7. Verify native first-launch conditions, agreement persistence, exit, browsing,
   keyboard navigation, System/Light/Dark and Help in an isolated local profile.
8. Upload candidates only to an unpublished GitHub draft. Run the same exact
   downloads and application tests on a clean GitHub Windows runner. Verify asset
   hashes before testing. Add beta feedback where available; document the tested
   OS and any remaining practical limits accurately.
9. Generate the final verification report. Update source/readiness documents and
   source ZIP/checksums after documentation changes. Tag the final source commit.
10. Publish the draft only after every required check passes. Present the EXE as
    the main download, ZIP as alternative, and source assets beside them. State
    that the app is unsigned. Verify public download links and artifact hashes.

Signing is optional for this release and is not claimed. A clean scan does not
establish SmartScreen reputation. Use a valid signing identity before describing
any later build as signed; calculate hashes only after signing.
