"""Explicit numerical protocol routing, independent of package release defaults."""
from __future__ import annotations

from importlib import import_module


DEFAULT_PROTOCOL = '0.2.0'
SUPPORTED_PROTOCOLS = ('0.1.0', '0.2.0')
CONFIG_FIELDS = ('seed', 'world', 'strategy', 'budget', 'noise')


class StudyCancelled(Exception):
    """Cooperative cancellation at a completed numerical checkpoint."""


def _engine(protocol: str):
    if protocol not in SUPPORTED_PROTOCOLS:
        raise ValueError(f'Unsupported numerical protocol: {protocol!r}')
    return import_module('.engine' if protocol == '0.1.0' else '.v2', __package__)


def normalize_request(flat_request: dict, *, default_protocol=DEFAULT_PROTOCOL) -> dict:
    if not isinstance(flat_request, dict):
        raise ValueError('Study request must be a dictionary')
    config = dict(flat_request)
    protocol = config.pop('protocol', default_protocol)
    if not isinstance(protocol, str) or protocol not in SUPPORTED_PROTOCOLS:
        raise ValueError(f'Unsupported numerical protocol: {protocol!r}')
    return {**_engine(protocol).validate_config(config), 'protocol': protocol}


def receipt_protocol(receipt: dict) -> str:
    """Historical evidence must specify its result version, never use today's default."""
    if not isinstance(receipt, dict) or not isinstance(receipt.get('result'), dict):
        raise ValueError('Malformed receipt result')
    result = receipt['result']
    version = result.get('version')
    if not isinstance(version, str) or version not in SUPPORTED_PROTOCOLS:
        raise ValueError(f'Unsupported recorded numerical protocol: {version!r}')
    for record in (receipt, result):
        if 'protocol' in record and record['protocol'] != version:
            raise ValueError('Recorded protocol and numerical result version disagree')
    return version


def run_study(flat_request: dict, progress=None, *, cancelled=None) -> dict:
    request = normalize_request(flat_request)
    protocol = request.pop('protocol')

    def checkpoint(fraction=None, message=None):
        if cancelled is not None and cancelled():
            raise StudyCancelled('Study cancelled at a numerical checkpoint')
        if fraction is not None and progress is not None:
            progress(fraction, message)
        if cancelled is not None and cancelled():
            raise StudyCancelled('Study cancelled at a numerical checkpoint')

    checkpoint()
    result = _engine(protocol).run_study(request, progress=checkpoint)
    checkpoint()
    return result


def replay_result(receipt: dict, progress=None) -> dict:
    from .evidence import verify_receipt
    verify_receipt(receipt)
    return run_study({**receipt['config'], 'protocol': receipt_protocol(receipt)}, progress=progress)
