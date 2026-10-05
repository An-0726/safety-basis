#!/usr/bin/env python3
"""Explicit complete-batch browser freeze, bounded by independently reviewed scope.

No existing fixture is rewritten. Source identities and all exact public sets
are derived from knowledge. Only individually authorized H/K withdrawals may
remove previous public entries or inherited rendered detail coverage.
"""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/pipeline/tests'), str(ROOT / 'tools/v4')]
from freeze_complete_remaining_history import (freeze as freeze_history, load_authorization,
    BASELINE, LOCAL_BASELINE, TREE, REPORTS, AUTHORIZATION, FIXTURE as HISTORY_FIXTURE)
from freeze_recovery_expectations import baseline_hashes, project_expectations
from residual_clause_acceptance import load_expectations, FIXTURE as PRIOR_FIXTURE
from recovery_release_acceptance import validate_expectations
from complete_remaining_acceptance import validate_preservation
from release_snapshot import FORMAL_NAMESPACES, source_hashes, snapshot_digest, stable_knowledge_snapshot


def freeze(root, as_of, source_ref=LOCAL_BASELINE):
    root = Path(root).resolve()
    history = freeze_history(root, source_ref)
    saved_history = json.loads((root / HISTORY_FIXTURE).read_text())
    if history != saved_history:
        raise AssertionError('History inverse must be frozen first and still match final source')
    authority = load_authorization(root)
    prior = load_expectations()
    _, predecessor = baseline_hashes(root, source_ref)
    predecessor = {p: v for p, v in predecessor.items()
                   if p == 'manifest.json' or any(p.startswith(ns + '/') for ns in FORMAL_NAMESPACES)}
    if snapshot_digest(predecessor) != prior['knowledgeSnapshotHash']:
        raise AssertionError('Predecessor does not match reviewed residual source snapshot')
    if as_of < date.fromisoformat(prior['asOf']):
        raise AssertionError('New fixture date precedes reviewed predecessor')
    baseline = dict(predecessor)
    for relative, change in prior['sourceChanges'].items():
        if predecessor.get(relative) != change['afterSha256']:
            raise AssertionError('Reviewed predecessor change hash mismatch: ' + relative)
        if change['beforeSha256'] is None:
            baseline.pop(relative, None)
        else:
            baseline[relative] = change['beforeSha256']
    with stable_knowledge_snapshot(root / 'knowledge') as (knowledge, digest):
        hashes = source_hashes(knowledge)
        expected_hashes = dict(predecessor)
        for path, row in history['records'].items():
            if not path.startswith('knowledge/'):
                continue
            relative = path.removeprefix('knowledge/')
            if relative == 'manifest.json' or any(relative.startswith(ns + '/') for ns in FORMAL_NAMESPACES):
                expected_hashes[relative] = row['afterSha256']
        if hashes != expected_hashes:
            raise AssertionError('Browser source no longer matches the explicitly authorized history freeze')
        result = project_expectations(knowledge, as_of, hashes=hashes,
            baseline_commit=prior['baselineCommit'], baseline=baseline)
        result['knowledgeSnapshotHash'] = digest
    validate_expectations(result)
    validate_preservation(result, prior, authority['withdrawals'])
    authored_hazards = set()
    for path in history['records']:
        parts = Path(path).parts
        if len(parts) == 3 and parts[:2] == ('knowledge', 'hazards'):
            authored_hazards.add(Path(path).stem)
    required = authored_hazards & set(result['expectedIds']['hazards'])
    if not required <= set(result['changedHazardIds']):
        raise AssertionError('Every authored formal hazard needs an exact rendered detail')
    batch_paths = {p.removeprefix('knowledge/') for p in history['records'] if p.startswith('knowledge/')}
    batch_hazards = {row['id'] for row in result['records'] if set(row['changedDependencies']) & batch_paths}
    if not required <= batch_hazards:
        raise AssertionError('Current-batch dependency closure misses authored formal hazards')
    audit_paths = [*REPORTS, AUTHORIZATION, HISTORY_FIXTURE, *authority['metadataPaths']]
    if authority.get('coverageIndexPath'):
        audit_paths.append(authority['coverageIndexPath'])
    result['batchAudit'] = {'schemaVersion': 'complete-remaining-browser-audit-v1',
        'baselineCommit': BASELINE, 'baselineTree': TREE,
        'predecessorFixtureSha256': hashlib.sha256(PRIOR_FIXTURE.read_bytes()).hexdigest(),
        'auditFileSha256': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in audit_paths},
        'withdrawals': authority['withdrawals'], 'requiredFormalHazardIds': sorted(required),
        'currentBatchHazardIds': sorted(batch_hazards)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    parser.add_argument('--source-ref', default=LOCAL_BASELINE)
    parser.add_argument('--out', type=Path, default=ROOT / 'tools/browser/fixtures/complete_remaining_20261005.json')
    args = parser.parse_args()
    result = freeze(args.root, args.as_of, args.source_ref)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(args.out), 'knowledgeSnapshotHash': result['knowledgeSnapshotHash'],
        'counts': {k: len(ids) for k, ids in result['expectedIds'].items()},
        'changedPublicHazards': len(result['records'])}))


if __name__ == '__main__':
    main()
