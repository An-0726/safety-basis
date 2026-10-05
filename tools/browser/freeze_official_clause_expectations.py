#!/usr/bin/env python3
"""Explicitly freeze current source while retaining all prior recovery coverage.

The supplied predecessor commit must reproduce the old fixture's full source
hash. Its original baseline is reconstructed from the old audited change hashes,
then unchanged source projection code selects both inherited and new coverage.
No old fixture, approval or production Gate is changed. Run only after source
review is quiescent; the new fixture needs independent review before release.
"""
import argparse
from datetime import date
import json
from pathlib import Path

from freeze_recovery_expectations import baseline_hashes, project_expectations
from recovery_release_acceptance import load_expectations, validate_expectations
from release_snapshot import FORMAL_NAMESPACES, source_hashes, snapshot_digest, stable_knowledge_snapshot

ROOT = Path(__file__).resolve().parents[2]


def freeze(root, as_of, predecessor_ref):
    prior = load_expectations()
    _, predecessor = baseline_hashes(root, predecessor_ref)
    predecessor = {p: v for p, v in predecessor.items()
                   if p == 'manifest.json' or any(p.startswith(ns + '/') for ns in FORMAL_NAMESPACES)}
    if snapshot_digest(predecessor) != prior['knowledgeSnapshotHash']:
        raise AssertionError('Predecessor does not match the reviewed recovery source snapshot')
    if as_of < date.fromisoformat(prior['asOf']):
        raise AssertionError('New fixture date precedes the reviewed recovery fixture')
    baseline = dict(predecessor)
    for relative, change in prior['sourceChanges'].items():
        if predecessor.get(relative) != change['afterSha256']:
            raise AssertionError('Reviewed predecessor change hash mismatch: ' + relative)
        if change['beforeSha256'] is None:
            baseline.pop(relative, None)
        else:
            baseline[relative] = change['beforeSha256']
    with stable_knowledge_snapshot(root / 'knowledge') as (knowledge, digest):
        result = project_expectations(knowledge, as_of, hashes=source_hashes(knowledge),
            baseline_commit=prior['baselineCommit'], baseline=baseline)
        result['knowledgeSnapshotHash'] = digest
    validate_expectations(result)
    missing = set(prior['changedHazardIds']) - set(result['changedHazardIds'])
    if missing:
        raise AssertionError('Inherited changed-detail browser coverage removed: ' + ', '.join(sorted(missing)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    parser.add_argument('--predecessor-ref', required=True)
    parser.add_argument('--out', type=Path, default=ROOT / 'tools/browser/fixtures/official_clauses_20261005.json')
    args = parser.parse_args()
    result = freeze(args.root.resolve(), args.as_of, args.predecessor_ref)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(args.out), 'knowledgeSnapshotHash': result['knowledgeSnapshotHash'],
        'counts': {k: len(ids) for k, ids in result['expectedIds'].items()},
        'changedPublicHazards': len(result['records'])}))


if __name__ == '__main__':
    main()
