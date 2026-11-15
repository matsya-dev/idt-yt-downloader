"""Copy complete runtime notices with unique paths; never flatten vendor licenses."""
import importlib.metadata as metadata
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('requests', 'beautifulsoup4', 'soupsieve', 'urllib3', 'certifi',
            'charset-normalizer', 'idna', 'typing-extensions', 'setuptools',
            'packaging', 'pyinstaller', 'yt-dlp', 'yt-dlp-ejs')


def collect(destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in PACKAGES:
        dist = metadata.distribution(name)
        for entry in dist.files or []:
            if any(word in entry.name.upper() for word in ('LICENSE', 'COPYING', 'NOTICE', 'AUTHORS')):
                path = dist.locate_file(entry)
                if path.is_file():
                    if Path(str(entry)).is_absolute() or '..' in Path(str(entry)).parts:
                        raise RuntimeError('Unsafe notice path: ' + str(entry))
                    target = destination / 'Python-packages' / name / Path(str(entry))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
    # The JS helper retains third-party attribution in its compiled library.
    dist = metadata.distribution('yt-dlp-ejs')
    for entry in dist.files:
        if entry.name == 'lib.min.js':
            text = dist.locate_file(entry).read_text(encoding='utf8')
            header = text.split('var lib=', 1)[0]
            if 'copyright' not in header.lower() or len(header) > 20000:
                raise RuntimeError('Inspect the changed EJS attribution format before building.')
            (destination / 'EJS-library-notices.txt').write_text(header, encoding='utf8')
    shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', destination / 'Python-license.txt')


if __name__ == '__main__':
    collect(ROOT / 'third-party')
