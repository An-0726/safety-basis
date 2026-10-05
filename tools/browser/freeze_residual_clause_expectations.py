#!/usr/bin/env python3
"""Freeze current residual source while preserving every prior reviewed detail.

The real official-batch predecessor is the default. A local --source-ref is
accepted only when its complete Git tree matches that predecessor. Prior change
hashes reconstruct the original browser baseline; the normal source projection
then derives all current IDs and details. No earlier fixture is rewritten.
"""
import argparse
from datetime import date
import json
from pathlib import Path
import subprocess

from freeze_recovery_expectations import baseline_hashes, project_expectations
from official_clause_acceptance import load_expectations
from recovery_release_acceptance import validate_expectations
from release_snapshot import FORMAL_NAMESPACES, source_hashes, snapshot_digest, stable_knowledge_snapshot

ROOT = Path(__file__).resolve().parents[2]
BASELINE = '23d0e0d415762ccb00341e9e0584c1694f15881d'
TREE = '84ed7015e73ba20ee505541ad94f776be48f31fd'


def freeze(root, as_of, source_ref=BASELINE):
    tree = subprocess.check_output(['git', 'rev-parse', source_ref + '^{tree}'], cwd=root, text=True).strip()
    if tree != TREE:
        raise AssertionError('Unexpected residual browser predecessor tree')
    prior = load_expectations()
    _, predecessor = baseline_hashes(root, source_ref)
    predecessor = {p: v for p, v in predecessor.items()
                   if p == 'manifest.json' or any(p.startswith(ns + '/') for ns in FORMAL_NAMESPACES)}
    if snapshot_digest(predecessor) != prior['knowledgeSnapshotHash']:
        raise AssertionError('Predecessor does not match the reviewed official-clause source snapshot')
    if as_of < date.fromisoformat(prior['asOf']):
        raise AssertionError('New fixture date precedes the reviewed official-clause fixture')
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
    parser.add_argument('--source-ref', default=BASELINE)
    parser.add_argument('--out', type=Path, default=ROOT / 'tools/browser/fixtures/residual_clauses_20261005.json')
    args = parser.parse_args()
    result = freeze(args.root.resolve(), args.as_of, args.source_ref)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(args.out), 'knowledgeSnapshotHash': result['knowledgeSnapshotHash'],
        'counts': {k: len(ids) for k, ids in result['expectedIds'].items()},
        'changedPublicHazards': len(result['records'])}))


if __name__ == '__main__':
    main()
