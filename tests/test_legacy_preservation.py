"""Published numerical evidence remains an immutable historical baseline."""
import hashlib
import json
from pathlib import Path


def test_published_v01_engine_paper_and_evidence_are_byte_identical():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / 'docs/legacy-v01-manifest.json').read_text(encoding='utf-8'))
    changed = [name for name, checksum in manifest['files'].items()
               if not (root / name).is_file()
               or hashlib.sha256((root / name).read_bytes()).hexdigest() != checksum]
    assert not changed, f'Published v0.1 artifacts changed: {changed}'
