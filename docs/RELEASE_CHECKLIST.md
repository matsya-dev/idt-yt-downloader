# Release checklist

The application source and the portable Windows package have separate release
checks. A passing functional test suite does not establish redistribution rights
for the standalone tools.

1. Run `python -m pytest -q` on Windows with the recorded tools available.
2. Run `python scripts/release_audit.py` to audit the source upload and create its
   clean source ZIP. Review `release/source-audit.json` before committing files.
3. Complete the dependency review in `docs/LICENSING_REVIEW.md`. A Windows download
   must have matching source access and complete notices for its bundled tools.
   The source repository may be published separately without those binaries.
4. Build with `python scripts/build.py`. That creates a LOCAL test package; it is
   not public-release approval. The package includes `DISTRIBUTION_STATUS.txt`.
5. Run `python scripts/verify_package.py` against the final ZIP. It checks all
   archive members and hashes and runs the extracted executable with a clean PATH.
6. Scan both the ZIP and extracted directory using Microsoft Defender. Preserve
   the exit code, scan date and result. A clean scan is not a code signature.
7. Test a browser-downloaded ZIP on other Windows x64 PCs without Python or FFmpeg
   installed. Check first launch, display scaling, source browsing, selected
   playlists, Unicode destinations, pause/close/reopen/resume and updates.
8. If signing, sign before calculating the final manifest and ZIP checksum, then
   repeat package verification and the malware scan. Do not change signed files.
9. Create a GitHub release draft. Include the exact version, Windows x64 support,
   known limits, checksums, instructions, notices and corresponding-source links
   immediately beside the binary download. Attach no local profiles or test media.
10. Publish the binary only after the licensing and recipient-machine checks pass.
    Keep older releases and the previous known-working package available.

On 15 November 2026, the 2.3.0 application passes its functional checks. Public
binary release is held for the corresponding-source inventory and recipient-PC
testing. See `docs/LICENSING_REVIEW.md` for specific unresolved items.
