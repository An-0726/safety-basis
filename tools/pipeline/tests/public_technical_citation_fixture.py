"""Exact, fail-closed test-only inverse of the bounded technical-citation repairs.

No production Gate or source is changed. Unknown additions remain visible.
"""
import copy
import hashlib
import json
from pathlib import Path
F = json.loads((Path(__file__).parent/'fixtures/public_technical_citations_20261003.json').read_text())

def pre_technical_ids(kind, ids):
    return set(ids) - set(F['addedIds'].get(kind, []))

def pre_technical_inventory(kind, rows):
    return [(ident, state) for ident, state in rows if ident not in F['addedIds'].get(kind, [])]

def pre_technical_source_bytes(path, raw):
    row = F['records'].get(path)
    if row is None:
        return raw
    if hashlib.sha256(raw).hexdigest() != row['afterSha256']:
        raise AssertionError('unexpected technical citation source change: ' + path)
    if row['beforeFileText'] is None:
        return None
    before = row['beforeFileText'].encode()
    if hashlib.sha256(before).hexdigest() != row['beforeSha256']:
        raise AssertionError('corrupt technical citation historical source: ' + path)
    return before

def pre_technical_manifest(manifest):
    old = copy.deepcopy(manifest)
    receipt = F['manifestReceipt']
    rows = [r for r in old.get('batches', []) if r.get('id') == receipt['id']]
    if not rows:
        return old  # Historical/synthetic fixture with no batch receipt.
    if rows != [receipt]:
        raise AssertionError('technical citation manifest receipt drift')
    old['batches'].remove(receipt)
    for kind, ids in F['addedIds'].items():
        old['counts'][kind] -= len(ids)
        if kind in old:
            old[kind] -= len(ids)
    return old

def pre_technical_gate(gate):
    prior = copy.deepcopy(gate)
    delta = F['gateSnapshots'].get(str(getattr(gate, 'as_of', '')))
    if delta is None or not set(delta['changedLinks']) & set(gate.links):
        return prior
    for kid, row in delta['changedLinks'].items():
        if gate.links.get(kid) != row['after']:
            raise AssertionError('technical citation Gate judgment drift: ' + kid)
        if row['before'] is None:
            prior.links.pop(kid, None)
        else:
            prior.links[kid] = copy.deepcopy(row['before'])
    for key, added, removed in [('eligible_hazards','hazardsAdded','hazardsRemoved'),
                                ('eligible_links','linksAdded','linksRemoved')]:
        values = set(getattr(gate,key))
        if not set(delta[added]) <= values or set(delta[removed]) & values:
            raise AssertionError('technical citation membership drift: ' + key)
        setattr(prior,key,(values-set(delta[added]))|set(delta[removed]))
    return prior
