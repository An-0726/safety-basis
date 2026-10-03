"""Explicit next-batch projection for older tests only, never Gate policy.

Only pinned IDs are removed. Unknown additions and unrelated changes stay visible.
"""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from public_technical_citation_fixture import (pre_technical_ids, pre_technical_inventory, pre_technical_manifest, pre_technical_gate)
from training_citation_fixture import pre_training_gate, pre_training_inventory
from remaining_clause_fixture import pre_remaining_gate, pre_remaining_inventory
from occupational_citation_fixture import pre_occupational_gate, pre_occupational_inventory

FIXTURE = json.loads((Path(__file__).parent/'fixtures/common_hazards_cohort_20261003.json').read_text())
FOLDERS = {'laws':'laws','lawVersions':'law-versions','clauses':'clauses','hazards':'hazards',
           'links':'links','evidence':'evidence','successions':'successions','requirements':'requirements'}
ADDED_IDS = {FOLDERS[k]:frozenset(v) for k,v in FIXTURE['addedEntityIds'].items()}
ADMITTED_IDS = frozenset(FIXTURE['admittedHazardIds'])

def pre_common_ids(kind, ids):
    return pre_technical_ids(kind, ids)-ADDED_IDS.get(kind,frozenset())

def pre_common_inventory(kind, rows):
    return sorted((ident,'proposed' if kind=='hazards' and ident=='H004' else state)
                  for ident,state in pre_training_inventory(kind, pre_occupational_inventory(kind, pre_remaining_inventory(kind, pre_technical_inventory(kind, rows)))) if ident not in ADDED_IDS.get(kind,frozenset()))

def pre_common_manifest(manifest):
    old=pre_technical_manifest(manifest)
    for key,ids in FIXTURE['addedEntityIds'].items():
        old['counts'][key]-=len(ids)
        if key in old: old[key]-=len(ids)
    for state,delta in FIXTURE['lifecycleDelta'].items():
        old['lifecycle'][state]-=delta
        if state+'Hazards' in old: old[state+'Hazards']-=delta
    if old.get('batch')==FIXTURE['batchId']: old['batch']='commerce-candidate-dispositions-20261002'
    return old

def pre_common_gate(gate):
    # Keep the date and diagnostic rows for the preceding citation projection.
    gate = pre_training_gate(pre_occupational_gate(pre_remaining_gate(pre_technical_gate(gate))))
    prior = copy.deepcopy(gate)
    prior.eligible_hazards = set(gate.eligible_hazards) - ADMITTED_IDS
    prior.eligible_links = set(gate.eligible_links) - ADDED_IDS['links']
    return prior
