"""Archive the complete current project and papers with a byte-level manifest."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'output/pdf/counterform_v02_paper_sources.zip'
EXCLUDED = {'publications/v02/counterform_v02_paper_sources.zip', 'publications/v02/publication-manifest.json'}


def main():
    try:
        git_root = subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,stderr=subprocess.DEVNULL).decode().strip()
        if Path(git_root).resolve() != ROOT: raise ValueError('Extracted source has no own Git checkout')
        listed = subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT)
        names = sorted(set(name.decode('utf-8') for name in listed.split(b'\0') if name))
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        # The published ZIP is self-contained and deliberately excludes Git internals.
        names = sorted(json.loads((ROOT/'source-manifest.json').read_bytes())['files'])
    if any(not (ROOT/name).resolve().is_relative_to(ROOT) for name in names):
        raise ValueError('Source manifest contains a path outside the project')
    files = {name:(ROOT/name).read_bytes() for name in names if name not in EXCLUDED and (ROOT/name).is_file()}
    assert 'publications/v02/counterform_v02_development_paper.pdf' in files
    assert len([name for name in files if name.startswith('runs/v02-development-20261103/') and name.endswith('/receipt.json')]) == 48
    manifest = {'schema':'counterform.paper-source.v2','notes':[
        'Complete project working-tree snapshot with both papers and all recorded studies.',
        'The archive itself and its external publication manifest are excluded to prevent recursive hashing.',
        'Checksums establish byte correspondence, not authenticity or physical validity.'],
        'files':{name:hashlib.sha256(data).hexdigest() for name,data in files.items()}}
    files['source-manifest.json'] = json.dumps(manifest,indent=2,sort_keys=True).encode('utf-8')
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(TARGET,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in sorted(files.items()):
            info=zipfile.ZipInfo(name,(2026,11,3,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(info,data)
    with zipfile.ZipFile(TARGET) as archive:
        assert set(archive.namelist()) == set(files)
        for name,expected in manifest['files'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
    print(json.dumps({'archive':str(TARGET),'files_verified':len(manifest['files']),'bytes':TARGET.stat().st_size}))


if __name__=='__main__':
    main()
