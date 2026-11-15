"""Compatibility entry point for verifying the portable ZIP alternative."""
import sys,tempfile,json
from pathlib import Path
from verify_portable import verify_zip,ROOT,ARCHIVE_NAME,__version__

if __name__=='__main__':
    path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'release'/f'{ARCHIVE_NAME}-{__version__}-Windows-x64.zip'
    target=Path(tempfile.mkdtemp(prefix='ZIP check తెలుగు ',dir=ROOT/'qa'))
    print(json.dumps(verify_zip(path,target,network=True),indent=2))
