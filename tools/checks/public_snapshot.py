#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One reviewed line per public hazard: a content fingerprint plus its title.

The committed snapshot is the reviewable record of what the site publishes. A
pull request that changes any public rule must also change its line here, so the
Git diff of this file lists exactly which rules were added, removed or changed.

  python tools/checks/public_snapshot.py --bundle source/releases/current --check
  python tools/checks/public_snapshot.py --bundle source/releases/current --write
  python tools/checks/public_snapshot.py --changed-since origin/main
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = Path(__file__).with_name('public-snapshot.json')
HAZARD_FIELDS = ('title', 'description', 'measures', 'conditions', 'category', 'places', 'mode')
BASIS_FIELDS = ('linkId', 'role', 'clauseId', 'applicability', 'jurisdictionCode')
CLAUSE_FIELDS = ('article', 'quote', 'content', 'lawId', 'status', 'region')


def shard_records(folder):
    records = {}
    for path in sorted(folder.glob('*.json')):
        for record in json.loads(path.read_text(encoding='utf-8'))['records']:
            records[record['id']] = record
    return records


def project(bundle):
    data = Path(bundle) / 'data'
    hazards, clauses = shard_records(data / 'hazards'), shard_records(data / 'clauses')
    lines = {}
    for hazard_id, hazard in sorted(hazards.items()):
        basis = []
        for ref in hazard.get('basisRefs', []):
            clause = clauses[ref['clauseId']]
            basis.append({**{key: ref.get(key) for key in BASIS_FIELDS},
                          'clause': {key: clause.get(key) for key in CLAUSE_FIELDS}})
        payload = {**{key: hazard.get(key) for key in HAZARD_FIELDS},
                   'basis': sorted(basis, key=lambda row: row['linkId'])}
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        lines[hazard_id] = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16] + ' ' + hazard['title']
    return {'schemaVersion': 'public-snapshot-v1', 'hazardCount': len(lines), 'hazards': lines}


def difference(before, after):
    old, new = before['hazards'], after['hazards']
    return {'added': sorted(set(new) - set(old)), 'removed': sorted(set(old) - set(new)),
            'changed': sorted(key for key in set(old) & set(new) if old[key] != new[key])}


def load(path=SNAPSHOT):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def at_ref(ref):
    relative = SNAPSHOT.relative_to(ROOT).as_posix()
    result = subprocess.run(['git', '-C', str(ROOT), 'show', f'{ref}:{relative}'], capture_output=True)
    if result.returncode:
        return None
    return json.loads(result.stdout.decode('utf-8'))


def describe(delta, before, after):
    for kind in ('added', 'changed', 'removed'):
        for hazard_id in delta[kind]:
            line = (before if kind == 'removed' else after)['hazards'][hazard_id]
            print(f'{kind:8} {hazard_id}  {line.split(" ", 1)[1]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--changed-since', metavar='REF')
    args = parser.parse_args()
    if args.changed_since:
        before = at_ref(args.changed_since)
        # No snapshot at that commit means there is nothing to compare with, not that every rule is new.
        delta = difference(before, load()) if before else {'added': [], 'changed': []}
        print(','.join(delta['added'] + delta['changed']))
        return 0
    if not args.bundle:
        parser.error('--bundle is required with --check and --write')
    current = project(args.bundle)
    if args.write:
        with open(SNAPSHOT, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(current, ensure_ascii=False, indent=0) + '\n')
        print(f'wrote {current["hazardCount"]} public hazards')
        return 0
    committed = load()
    delta = difference(committed, current)
    if any(delta.values()):
        describe(delta, committed, current)
        print('\nPublic content differs from tools/checks/public-snapshot.json. If every line above is intended, '
              'run public_snapshot.py --write and commit the file.', file=sys.stderr)
        return 1
    print(f'public snapshot matches: {current["hazardCount"]} hazards')
    return 0


if __name__ == '__main__':
    sys.exit(main())
