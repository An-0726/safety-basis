"""Test-only pre-commerce cohort views, never publication/Gate authorization.

The fixture lists IDs reviewed against 26b6c3e, not whatever is new at runtime.
Unknown additions and changes to every non-cohort row remain visible to the
historical assertions. The current batch has separate exact-delta tests.
"""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from citation_cohort_fixture import (pre_citation_ids, pre_citation_inventory,
                                    pre_citation_manifest, pre_citation_gate)

from common_hazards_fixture import (pre_common_ids, pre_common_inventory,
                                    pre_common_manifest, pre_common_gate)

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' /
                      'commerce_admission_cohort_20261002.json').read_text(encoding='utf-8'))
FOLDERS = {'laws': 'laws', 'lawVersions': 'law-versions', 'clauses': 'clauses',
           'hazards': 'hazards', 'links': 'links', 'evidence': 'evidence',
           'successions': 'successions'}
ADDED_IDS = {FOLDERS[key]: frozenset(ids) for key, ids in FIXTURE['addedEntityIds'].items()}
CANDIDATE_IDS = frozenset(FIXTURE['candidateSources'])
ADMITTED_IDS = frozenset(FIXTURE['admittedHazardIds'])


def pre_commerce_ids(kind, ids):
    """Exclude only this batch's explicit IDs; never infer another batch's delta."""
    return pre_common_ids(kind, pre_citation_ids(kind, ids)) - ADDED_IDS.get(kind, frozenset())


def pre_commerce_inventory(kind, rows):
    """Restore only the 44 pre-existing candidates' historical lifecycle view."""
    return sorted((ident, 'proposed' if kind == 'hazards' and ident in CANDIDATE_IDS
                   else lifecycle) for ident, lifecycle in pre_common_inventory(kind, pre_citation_inventory(kind, rows))
                  if ident not in ADDED_IDS.get(kind, frozenset()))


def pre_commerce_manifest(manifest):
    """Copy historical counts; leave the real manifest and all Gate data alone."""
    historical = pre_common_manifest(pre_citation_manifest(manifest))
    for key, ids in FIXTURE['addedEntityIds'].items():
        historical['counts'][key] -= len(ids)
        if key in historical:
            historical[key] -= len(ids)
    for lifecycle, delta in FIXTURE['lifecycleDelta'].items():
        historical['lifecycle'][lifecycle] -= delta
        key = lifecycle + 'Hazards'
        if key in historical:
            historical[key] -= delta
    # Preserve the historical batch identity, without assigning future batches
    # to this cohort or interpreting their counts as approved commerce records.
    if historical.get('batch') == FIXTURE['batchId']:
        historical['batch'] = 'civil-fireworks-reference-reading-20261001'
    return historical


def pre_commerce_gate(result):
    """Project an already-evaluated Gate result; do not patch Gate or reviews.

    Callers recompute used clauses from the remaining links, so a shared old
    clause is retained even when another new commerce link also uses it.
    """
    result = pre_common_gate(pre_citation_gate(result))
    return SimpleNamespace(eligible_hazards=set(result.eligible_hazards) - ADMITTED_IDS,
                           eligible_links=set(result.eligible_links) - ADDED_IDS['links'],
                           links=result.links)
