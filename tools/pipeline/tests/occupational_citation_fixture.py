"""Exact test-only inverse of the Article 25 repair for older baseline contracts.

Never changes the production Gate or source. Changed inputs must equal the frozen
new record/judgment before inversion; unknown changes remain observable.
"""
import copy
import hashlib
import json
from pathlib import Path
F=json.loads((Path(__file__).parent/'fixtures/occupational_citation_repair_20261003.json').read_text())
ENTITIES={r['path']:r for r in F['entities']}
def pre_occupational_source_bytes(path,raw):
    row=ENTITIES.get(path)
    if row is None:return raw
    if hashlib.sha256(raw).hexdigest()!=row['fileSha256']:
        raise AssertionError(f'unexpected Article 25 source change: {path}')
    return row['beforeFileText'].encode()
def pre_occupational_inventory(kind,rows):
    result=[]
    for ident,state in rows:
        row=ENTITIES.get(f'knowledge/{kind}/{ident}.json')
        if row and 'lifecycle' in row['modifiedFields']:
            if state!=row['record']['lifecycle']:raise AssertionError(f'unexpected Article 25 lifecycle: {ident}')
            state=row['before']['lifecycle']
        result.append((ident,state))
    return result
def pre_occupational_gate(gate):
    prior=copy.deepcopy(gate)
    links=getattr(gate,'links',{})
    for kid,row in F['gateLinkTransitions'].items():
        if kid not in links:continue # Tiny synthetic examples have no cohort rows.
        if links[kid]!=row['after']:raise AssertionError(f'unexpected Article 25 link judgment: {kid}')
        prior.links[kid]=copy.deepcopy(row['before'])
    return prior
