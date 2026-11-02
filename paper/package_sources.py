"""Package the paper, reproducible analysis and original evidence with hashes."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'output' / 'pdf' / 'counterform_paper_sources.zip'


def main():
    files = {}
    def add(path, name=None):
        files[name or path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for p in sorted((ROOT / 'paper').rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            add(p)
    for prefix in ('runs/benchmark', 'runs/example', 'web', 'counterform/web'):
        for p in sorted((ROOT / prefix).rglob('*')):
            if p.is_file(): add(p)
    for folder in ('counterform', 'tests'):
        for p in sorted((ROOT / folder).glob('*.py')): add(p)
    for name in ('pyproject.toml', 'requirements-validated.txt', 'requirements-lock.txt', 'package.json', 'package-lock.json', 'vite.config.js', 'launch.ps1', 'run.bat'):
        add(ROOT / name)
    for name in ('research.md', 'results.md', 'verification.md'):
        add(ROOT / 'docs' / name)
    add(ROOT / 'paper' / 'README.md', 'README.md')
    add(ROOT / 'output' / 'pdf' / 'counterform_pilot_paper.pdf')
    manifest = {'schema': 'counterform.paper-source.v1', 'files': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(files.items())}}
    files['source-manifest.json'] = json.dumps(manifest, indent=2, sort_keys=True).encode()
    with zipfile.ZipFile(OUTPUT, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 2, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    with zipfile.ZipFile(OUTPUT) as z:
        assert set(z.namelist()) == set(files)
        for name, checksum in manifest['files'].items():
            assert hashlib.sha256(z.read(name)).hexdigest() == checksum, name
    print(json.dumps({'archive': str(OUTPUT), 'files_verified': len(manifest['files']), 'bytes': OUTPUT.stat().st_size}))


if __name__ == '__main__':
    main()
