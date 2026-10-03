"""Exact test-only inverse for 24-clause repairs, never publication policy.

Known files and judgments must equal the frozen reviewed successor before their
old values are exposed. Unknown additions or changes are never filtered away.
"""
from public_technical_citation_fixture import pre_technical_source_bytes
import copy
import hashlib
import json
from pathlib import Path
F = json.loads((Path(__file__).parent / 'fixtures/remaining_clause_repair_20261003.json').read_text())
ENTITIES = {r['path']: r for r in F['entities']}
REVIEWS = {r['path']: r for r in F['reviews']}

def pre_remaining_source_bytes(path, raw):
    raw = pre_technical_source_bytes(path, raw)
    row = ENTITIES.get(path) or REVIEWS.get(path)
    if row is None:
        return raw
    if hashlib.sha256(raw).hexdigest() != row['fileSha256']:
        raise AssertionError('unexpected remaining-clause source mutation: ' + path)
    before = row['beforeFileText'].encode()
    expected = row.get('oldFileSha256', row.get('previousFileSha256'))
    if hashlib.sha256(before).hexdigest() != expected:
        raise AssertionError('corrupt remaining-clause historical snapshot: ' + path)
    return before

def pre_remaining_inventory(kind, rows):
    prior = []
    for ident, state in rows:
        row = ENTITIES.get(f'knowledge/{kind}/{ident}.json')
        if row and 'lifecycle' in row['modifiedFields']:
            if state != row['record']['lifecycle']:
                raise AssertionError('unexpected remaining-clause lifecycle: ' + ident)
            state = row['before']['lifecycle']
        prior.append((ident, state))
    return prior

def pre_remaining_gate(result):
    prior = copy.deepcopy(result)
    day = str(getattr(result, 'as_of', ''))
    if day not in F['gateSnapshots']:
        return prior
    delta = F['gateSnapshots'][day]['changedLinks']
    if not set(delta) & set(result.links):
        return prior  # Unrelated synthetic fixtures contain no cohort IDs.
    for kid, row in delta.items():
        if result.links.get(kid) != row['after'] or kid not in result.eligible_links:
            raise AssertionError('unexpected remaining-clause judgment or membership: ' + kid)
        prior.links[kid] = copy.deepcopy(row['before'])
    return prior
