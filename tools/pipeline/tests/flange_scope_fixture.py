"""Exact inverse of three reviewed hazard edits for older inheritance pins only.

This is a test fixture, never production Gate policy. It rejects drift before
mapping an explicitly pinned final file back to its exact historical bytes.
Unknown files and unrelated changes stay visible to the older assertion.
"""
import hashlib
import json
from pathlib import Path

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' /
                     'flange_scope_corrections_20261003.json').read_text(encoding='utf-8'))
HAZARD_EDITS = {r['path']: r for r in FIXTURE['entities'] if '/hazards/' in r['path']}


def pre_flange_source_bytes(path, raw):
    row = HAZARD_EDITS.get(path)
    if row is None:
        return raw
    if hashlib.sha256(raw).hexdigest() != row['fileSha256']:
        raise AssertionError('flange final source drift: ' + path)
    previous = row['beforeFileText'].encode('utf-8')
    if hashlib.sha256(previous).hexdigest() != row['oldFileSha256']:
        raise AssertionError('flange historical source drift: ' + path)
    return previous
