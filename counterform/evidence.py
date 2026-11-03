"""Portable evidence records, integrity checks and conceptual CAD exports.

Checksums detect accidental or uncoordinated changes, not a malicious author
who can rewrite the entire archive. They are not signatures or physical proofs.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import html
import io
import json
from pathlib import Path, PurePosixPath
import platform
import re
import zipfile

import numpy as np
import scipy

from . import __version__


MAX_ARCHIVE_BYTES = 32_000_000
MAX_RECEIPT_BYTES = 25_000_000
MAX_MEMBER_BYTES = 25_000_000
MAX_MANIFEST_BYTES = 64_000
MAX_EXPANDED_BYTES = 30_000_000


def read_evidence(path: Path, *, max_bytes: int | None = None) -> bytes:
    """Bound the actual read, including files changed after the initial size check."""
    path = Path(path)
    limit = max_bytes if max_bytes is not None else (MAX_ARCHIVE_BYTES if path.suffix.lower() == '.zip' else MAX_RECEIPT_BYTES)
    if path.stat().st_size > limit:
        raise ValueError('Evidence exceeds file size limit')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Evidence exceeds file size limit')
    return data


def parse_json(data: bytes | str):
    def mapping(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f'Duplicate JSON field: {key}')
            value[key] = item
        return value

    def invalid(value):
        raise ValueError(f'Nonfinite JSON number: {value}')

    try:
        return json.loads(data, object_pairs_hook=mapping, parse_constant=invalid)
    except (RecursionError, OverflowError) as exc:
        raise ValueError('Evidence JSON exceeds supported nesting or numeric bounds') from exc


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_digest() -> str:
    source = Path(__file__).parent
    paths = sorted(source.rglob('*.py'), key=lambda p: p.relative_to(source).as_posix())
    return digest(b''.join(p.relative_to(source).as_posix().encode() + b'\0' + p.read_bytes() + b'\0' for p in paths))


def make_receipt(result: dict) -> dict:
    result = deepcopy(result)
    record = {
        'schema': 'counterform.receipt.v1',
        'software': {'counterform': __version__, 'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__, 'source_sha256': source_digest()},
        'config': result['config'], 'result': result,
        'result_sha256': digest(canonical(result)),
    }
    record['payload_sha256'] = digest(canonical(record))
    return record


def verify_receipt(receipt: dict) -> dict:
    if not isinstance(receipt, dict) or receipt.get('schema') != 'counterform.receipt.v1':
        raise ValueError('Unsupported receipt schema')
    try:
        record = {k: v for k, v in receipt.items() if k != 'payload_sha256'}
        if digest(canonical(record)) != receipt.get('payload_sha256'):
            raise ValueError('Receipt payload checksum mismatch')
        if not isinstance(receipt.get('result'), dict) or not isinstance(receipt.get('config'), dict):
            raise ValueError('Malformed receipt result or configuration')
        if digest(canonical(receipt['result'])) != receipt.get('result_sha256'):
            raise ValueError('Numerical result checksum mismatch')
        if receipt['config'] != receipt['result']['config']:
            raise ValueError('Receipt configuration mismatch')
    except (KeyError, TypeError, RecursionError, OverflowError) as exc:
        raise ValueError(f'Malformed evidence receipt: {exc}') from exc
    return {'valid': True, 'result_sha256': receipt['result_sha256'], 'scope': 'Integrity only; use replay for numerical recomputation.'}


def design_document(design: dict) -> dict:
    for key in ('mass', 'stiffness', 'damping'):
        if not np.isfinite(design[key]) or design[key] <= 0:
            raise ValueError(f'Invalid design {key}')
    return {
        'schema': 'counterform.conceptual-cad.v1', 'units': 'mm',
        'description': 'Illustrative four-body assembly. Spring/damper shown schematically; no stiffness-to-manufacturing mapping.',
        'physical_parameters_SI': design,
        'bodies': [
            {'name': 'base', 'origin': [0, 0, 0], 'size': [160, 100, 8]},
            {'name': 'primary_mass', 'origin': [45, 25, 35], 'size': [70, 50, 30]},
            {'name': 'absorber_mass', 'origin': [65, 35, 100], 'size': [30, 30, 20 + 60 * design['mass']]},
            {'name': 'schematic_connection', 'origin': [77, 47, 65], 'size': [6, 6, 35]},
        ],
        'limitations': ['Conceptual geometry only', 'No verified material, stress, fatigue, tolerances or manufacturability', 'STL dimensions are millimetres; STL has no intrinsic unit metadata'],
    }


def design_stl(design: dict) -> str:
    lines = ['solid counterform_concept_mm']
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    for body in design_document(design)['bodies']:
        origin = np.array(body['origin'], float)
        size = np.array(body['size'], float)
        vertices = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], float) * size + origin
        for indices in faces:
            a, b, c = vertices[list(indices)]
            normal = np.cross(b - a, c - a)
            normal /= np.linalg.norm(normal)
            lines.append('  facet normal ' + ' '.join(f'{n:.8g}' for n in normal))
            lines.append('    outer loop')
            lines.extend('      vertex ' + ' '.join(f'{n:.8g}' for n in point) for point in (a, b, c))
            lines.extend(['    endloop', '  endfacet'])
    return '\n'.join(lines + ['endsolid counterform_concept_mm', ''])


def report_html(receipt: dict) -> str:
    verify_receipt(receipt)
    r = receipt['result']
    esc = lambda value: html.escape(str(value))
    recorded_version = r.get('version', receipt.get('software', {}).get('counterform', 'unknown'))
    rows = ''.join(f'<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>' for k, v in r['summary'].items())
    recommendation = r.get('recommendation')
    recommendation_html = ''
    if isinstance(recommendation, dict):
        reasons = ''.join(f'<li>{esc(reason)}</li>' for reason in recommendation.get('reasons', []))
        recommendation_html = (f'<h2>Recommendation: {esc(recommendation.get("status", "unrecorded"))}</h2>'
            f'<p>{esc(recommendation.get("message", ""))}</p><ul>{reasons}</ul>'
            f'<p>Recorded recommendation control: {esc(recommendation.get("selected_control", "unrecorded"))}. '
            'Selected-design reductions below remain exploratory outcomes when the recommendation abstains.</p>')
    def flag(model, key):
        return 'not recorded' if key not in model else ('pass' if model[key] else 'reject')
    audits = ''.join(f'<tr><td>{esc(m.get("name"))}</td><td>{esc(m.get("audit_nrmse", "not recorded"))}</td>'
        f'<td>{esc(flag(m, "force_passed"))}</td><td>{esc(m.get("forecast_nrmse", "not recorded"))}</td>'
        f'<td>{esc(flag(m, "forecast_passed"))}</td><td>{esc(flag(m, "adequate"))}</td></tr>' for m in r.get('models', []))
    acquisitions = ''.join(f'<tr><td>{esc(e.get("index"))}</td><td>{esc(e.get("frequency"))}</td>'
        f'<td>{esc(e.get("amplitude"))}</td><td>{esc(e.get("selector", {}).get("score_label", "legacy heuristic"))}</td>'
        f'<td>{esc(e.get("score"))}</td><td>{len(e.get("candidates", []))}</td></tr>' for e in r.get('experiments', []))
    challenges = ''.join(f'<tr><td>{esc(c.get("name"))}</td><td>{c.get("baseline_rms", 0):.5g}</td><td>{c.get("design_rms", 0):.5g}</td><td>{c.get("reduction_pct", 0):.2f}%</td></tr>' for c in r.get('challenges', []))
    limits = ''.join(f'<li>{esc(v)}</li>' for v in r.get('limitations', []))
    response = r.get('response', {})
    curves = ''
    all_y = [v for key in ('baseline', 'selected', 'nominal') for v in response.get(key, [])]
    peak = max(all_y, default=1) or 1
    for key, color in [('baseline', '#a1a4ac'), ('selected', '#daaf48'), ('nominal', '#76b2ba')]:
        values = response.get(key, [])
        points = ' '.join(f'{30 + i * 700 / max(len(values)-1, 1):.2f},{220 - v / peak * 190:.2f}' for i, v in enumerate(values))
        curves += f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>'
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>COUNTERFORM evidence</title>
<style>body{{background:#171a1d;color:#e7e4da;font:16px system-ui;max-width:1000px;margin:50px auto;padding:0 24px}}h1{{letter-spacing:.08em}}small,p{{color:#b7b6ae}}table{{width:100%;border-collapse:collapse;margin:24px 0}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #3b3e40}}code{{overflow-wrap:anywhere}}svg{{width:100%;background:#202428;border:1px solid #404244}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}a{{color:#daaf48}}</style>
<h1>COUNTERFORM</h1><p>Local synthetic evidence report · simulation v{esc(recorded_version)} · exporter v{esc(__version__)}</p>
<p>Finite model selection and conceptual absorber design. This report establishes neither a novel research result nor real-world engineering reliability.</p>
<h2>Configuration</h2><pre>{esc(json.dumps(r['config'], indent=2))}</pre>
{recommendation_html}
<h2>Computed outcome</h2><table>{rows}</table>
<h2>Frozen model audits</h2><p>Passing flags are finite engineering diagnostics. Missing historical forecast fields are not inferred.</p><table><tr><th>Law</th><th>Force NRMSE</th><th>Force audit</th><th>Forecast NRMSE</th><th>Forecast audit</th><th>Recorded adequacy</th></tr>{audits}</table>
<h2>Acquisition diagnostics</h2><p>All retained candidate scores, fantasy assumptions and selection flags are available in the receipt; negative gains are retained.</p><table><tr><th>Experiment</th><th>rad/s</th><th>N</th><th>Score definition</th><th>Score</th><th>Menu candidates</th></tr>{acquisitions}</table>
<h2>Approximate frequency response</h2><p>Grey: baseline · amber: selected · blue: nominal. Horizontal axis: increasing angular frequency (rad/s); vertical axis: peak displacement (m) under 1.5 N forcing. Search approximation, separate from nonlinear challenges.</p><svg viewBox="0 0 760 240" role="img" aria-label="Frequency response comparison">{curves}</svg>
<h2>Held-out challenges</h2><table><tr><th>Condition</th><th>Baseline RMS (m)</th><th>Selected RMS (m)</th><th>Reduction</th></tr>{challenges}</table>
<h2>Validation</h2><pre>{esc(json.dumps(r.get('validation', {}), indent=2))}</pre>
<h2>Limits</h2><ul>{limits}</ul><p>STL/CAD exports are schematic, in millimetres, and not manufacturing specifications.</p>
<h2>Provenance</h2><pre>{esc(json.dumps(receipt['software'], indent=2))}</pre><p>Result SHA-256: <code>{receipt['result_sha256']}</code></p>
<p>Checksums detect changes relative to the manifest; they do not authenticate an author. Use the receipt and CLI replay to recompute numerical evidence.</p></html>'''


def build_bundle(receipt: dict) -> bytes:
    verify_receipt(receipt)
    design = receipt['result']['design']
    files = {
        'receipt.json': canonical(receipt),
        'design.json': canonical(design_document(design)),
        'design.stl': design_stl(design).encode(),
        'report.html': report_html(receipt).encode(),
        'README.txt': b'COUNTERFORM synthetic evidence. Verify: python -m counterform verify bundle.zip\nReplay: python -m counterform replay receipt.json\nCAD is conceptual; STL units are millimetres. No physical guarantee.\n',
    }
    manifest = {'schema': 'counterform.bundle.v1', 'files': {name: digest(value) for name, value in files.items()}}
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, value in {**files, 'manifest.json': canonical(manifest)}.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, value)
    return output.getvalue()


def verify_bundle(data: bytes) -> dict:
    try:
        if not isinstance(data, bytes) or len(data) > MAX_ARCHIVE_BYTES:
            raise ValueError('Archive exceeds evidence size limit')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            names = [i.filename for i in infos]
            for name in names:
                path = PurePosixPath(name)
                if path.is_absolute() or len(path.parts) != 1 or '..' in path.parts or '\\' in name or ':' in name:
                    raise ValueError('Unsafe archive path')
            if len(names) != len(set(names)):
                raise ValueError('Duplicate archive entry')
            if sum(i.file_size for i in infos) > MAX_EXPANDED_BYTES or len(infos) > 32:
                raise ValueError('Archive exceeds evidence size limit')
            for info in infos:
                limit = MAX_MANIFEST_BYTES if info.filename == 'manifest.json' else MAX_MEMBER_BYTES
                if info.file_size > limit:
                    raise ValueError(f'Archive member exceeds evidence size limit: {info.filename}')
                if info.flag_bits & 1:
                    raise ValueError('Encrypted evidence archives are unsupported')
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise ValueError('Unsupported evidence archive compression')

            def read_member(name):
                info = archive.getinfo(name)
                limit = MAX_MANIFEST_BYTES if name == 'manifest.json' else MAX_MEMBER_BYTES
                with archive.open(info) as source:
                    value = source.read(limit + 1)
                if len(value) > limit or len(value) != info.file_size:
                    raise ValueError(f'Archive member exceeds evidence size limit or declared size: {name}')
                return value

            if 'manifest.json' not in names:
                raise ValueError('Missing manifest')
            manifest = parse_json(read_member('manifest.json'))
            if not isinstance(manifest, dict) or manifest.get('schema') != 'counterform.bundle.v1':
                raise ValueError('Unsupported manifest schema')
            files = manifest.get('files', {})
            if not isinstance(files, dict):
                raise ValueError('Malformed manifest file mapping')
            expected = {'receipt.json', 'design.json', 'design.stl', 'report.html', 'README.txt'}
            if set(files) != expected or set(names) != expected | {'manifest.json'}:
                raise ValueError('Unexpected or missing archive entries')
            for name, checksum in files.items():
                if not isinstance(checksum, str) or re.fullmatch('[0-9a-f]{64}', checksum) is None:
                    raise ValueError(f'Malformed archive checksum: {name}')
                if digest(read_member(name)) != checksum:
                    raise ValueError(f'Archive checksum mismatch: {name}')
            verify_receipt(parse_json(read_member('receipt.json')))
            return {'valid': True, 'files_checked': len(files), 'scope': 'Integrity, not authenticity or physical verification'}
    except (zipfile.BadZipFile, KeyError, TypeError, json.JSONDecodeError, RuntimeError, NotImplementedError, EOFError) as exc:
        raise ValueError(f'Malformed evidence archive: {exc}') from exc
