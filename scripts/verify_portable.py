"""Exercise the standalone EXE and ZIP using only their own resources."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from vedaboat import APP_NAME,ARCHIVE_NAME,__version__


def run_self_test(exe,work,network=False):
    work.mkdir(parents=True,exist_ok=True)
    report=work/'self-test.json'
    env=os.environ.copy();env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')+';'+os.environ['SystemRoot']
    for key in ('PYTHONHOME','PYTHONPATH','TCL_LIBRARY','TK_LIBRARY'):env.pop(key,None)
    env['VEDABOAT_DATA_DIR']=str(work/'isolated-profile')
    command=[str(exe),'--self-test',str(report)]+(['--network'] if network else [])
    start=time.monotonic()
    result=subprocess.run(command,cwd=work,env=env,timeout=240,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    data=json.loads(report.read_text(encoding='utf8'))
    if result.returncode or not all(x['ok'] for x in data.values()):raise RuntimeError('Portable self-test failed: '+json.dumps(data))
    return dict(passed=True,checks={key:row['ok'] for key,row in data.items()},seconds=round(time.monotonic()-start,2))


def verify_zip(archive,work,network=False):
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise RuntimeError('ZIP CRC failure')
        manifest=json.loads(z.read(APP_NAME+'/checksums.json'))
        names={n for n in z.namelist() if not n.endswith('/')}
        if names!={APP_NAME+'/'+n for n in manifest}|{APP_NAME+'/checksums.json'}:raise RuntimeError('ZIP has unmanifested or missing files')
        for name,digest in manifest.items():
            if hashlib.sha256(z.read(APP_NAME+'/'+name)).hexdigest()!=digest:raise RuntimeError('ZIP component hash mismatch: '+name)
        for member in z.infolist():
            if not (work/member.filename).resolve().is_relative_to(work.resolve()):raise RuntimeError('Unsafe archive member')
        z.extractall(work)
    result=run_self_test(work/APP_NAME/(APP_NAME+'.exe'),work/'checks',network)
    result['verified_files']=len(manifest)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,default=ROOT/'release'/f'{ARCHIVE_NAME}-{__version__}-Windows-x64.exe')
    parser.add_argument('--zip',type=Path,default=ROOT/'release'/f'{ARCHIVE_NAME}-{__version__}-Windows-x64.zip')
    parser.add_argument('--network',action='store_true')
    parser.add_argument('--output',type=Path,default=ROOT/'qa'/'portable-verification.json')
    args=parser.parse_args();qa=ROOT/'qa';qa.mkdir(exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='Portable standalone తెలుగు ',dir=qa))
    single=work/'single EXE only';single.mkdir()
    moved=single/'Renamed downloader.exe';shutil.copy2(args.exe,moved)
    if list(single.iterdir())!=[moved]:raise RuntimeError('Standalone check folder is not empty')
    report={'version':__version__,'single_exe':run_self_test(moved,work/'first launch',args.network)}
    report['single_exe_relaunch']=run_self_test(moved,work/'second launch',False)
    report['zip']=verify_zip(args.zip,work/'ZIP alternative',args.network)
    report['single_exe_sha256']=hashlib.sha256(args.exe.read_bytes()).hexdigest()
    report['zip_sha256']=hashlib.sha256(args.zip.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
