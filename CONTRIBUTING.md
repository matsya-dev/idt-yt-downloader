# Contributing

Please keep changes within the simple manual audio-downloader scope. Open an
issue describing a bug or proposed change before adding features.

Use Windows x64 with Python 3.12+ and Tk. Install `requirements-dev.txt` in a
virtual environment. Fetch the recorded tools using `scripts/fetch_tools.py`,
then run `python -m pytest -q`. Tests use isolated local profiles and generated
media. Live media checks are separate scripts and must be run deliberately.

Keep the `vedaboat` Python module name, profile directory, source identities and
saved destination mappings compatible with existing users. Do not commit local
profiles, partial downloads, recordings, build outputs, secrets or QA logs.

Run `python scripts/release_audit.py` before preparing an upload. Follow
`docs/RELEASE_CHECKLIST.md` for distribution; packaging alone is not approval to
redistribute the third-party binaries.
