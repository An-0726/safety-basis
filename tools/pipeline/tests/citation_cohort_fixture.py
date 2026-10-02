"""Reconstruct only the explicit 2026-10-02 citation delta for older tests.

This module is test-only. It never changes source, reviews, or the production
Gate. Unknown additions/losses remain observable, and an altered affected Gate
row must match the frozen current judgment before its historical view is used.
"""
import copy
import json
from pathlib import Path

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' /
                     'public_citation_cohort_20261002.json').read_text(encoding='utf-8'))
ADDED_IDS = {k: frozenset(v) for k, v in FIXTURE['addedEntityIds'].items()}


def pre_citation_ids(kind, ids):
    return set(ids) - ADDED_IDS.get(kind, frozenset())


def pre_citation_inventory(kind, rows):
    changes = FIXTURE['lifecycleChanges'].get(kind, {})
    result = []
    for ident, lifecycle in rows:
        if ident in ADDED_IDS.get(kind, frozenset()):
            continue
        if ident in changes:
            expected = changes[ident]
            if lifecycle != expected['after']:
                raise AssertionError(f'unexpected lifecycle for citation cohort: {ident}')
            lifecycle = expected['before']
        result.append((ident, lifecycle))
    return sorted(result)


def pre_citation_manifest(manifest):
    historical = copy.deepcopy(manifest)
    folders = {'laws': 'laws', 'lawVersions': 'law-versions', 'clauses': 'clauses',
               'hazards': 'hazards', 'links': 'links', 'evidence': 'evidence',
               'successions': 'successions', 'requirements': 'requirements'}
    for key, kind in folders.items():
        delta = len(ADDED_IDS[kind])
        historical['counts'][key] -= delta
        if key in historical:
            historical[key] -= delta
    return historical


def pre_citation_gate(result):
    """Return the exact prior cohort; fail rather than mask unexpected changes."""
    # Tiny synthetic examples in other helper tests are outside this cohort.
    day = str(getattr(result, 'as_of', ''))
    if day not in FIXTURE['gateSnapshots']:
        return copy.deepcopy(result)
    delta = FIXTURE['gateSnapshots'][day]
    historical = copy.deepcopy(result)
    for kid, row in delta['changedLinks'].items():
        if result.links.get(kid) != row['after']:
            raise AssertionError(f'unexpected current citation link judgment: {kid}')
        if row['before'] is None:
            historical.links.pop(kid, None)
        else:
            historical.links[kid] = copy.deepcopy(row['before'])
    for key, added, removed in (
            ('eligible_hazards', 'hazardsAdded', 'hazardsRemoved'),
            ('eligible_links', 'linksAdded', 'linksRemoved')):
        values = set(getattr(result, key))
        if not set(delta[added]) <= values or set(delta[removed]) & values:
            raise AssertionError(f'unexpected current citation membership: {key}')
        setattr(historical, key, (values - set(delta[added])) | set(delta[removed]))
    return historical
