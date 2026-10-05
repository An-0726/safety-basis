#!/usr/bin/env python3
"""Explicitly freeze only the authorized 2026-10-05 batch's historical inverse.

Never run in CI to update expectations automatically. The three authored reports
bound the entity/evidence paths; only the four named publication metadata files
may be added. Unknown source changes abort instead of entering the inverse.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
REPORTS = [
    'docs/OFFICIAL_GENERAL_INTEGRATION_20261005.json',
    'docs/OFFICIAL_CYLINDER_GAS_INTEGRATION_20261005.json',
    'docs/OFFICIAL_EXPLOSION_INTEGRATION_20261005.json',
]
METADATA = ['knowledge/manifest.json', 'source/publication/law-index.json',
            'docs/PROJECT_STATE.md', 'docs/HANDOFF.md']
BASELINE = '792d0c9c0ee553e8e0a0312a9a190d82baccf4d1'
TREE = '3867f248ac7cc7e7e660db404bb0dc2c6bd1d62a'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def freeze(root, source_ref=BASELINE):
    tree = subprocess.check_output(['git', 'rev-parse', source_ref + '^{tree}'], cwd=root, text=True).strip()
    if tree != TREE:
        raise AssertionError('Unexpected official-clause predecessor tree')
    allowed = set(METADATA)
    for relative in REPORTS:
        report = json.loads((root / relative).read_text())
        if report['baselineTree'] != TREE:
            raise AssertionError('Authored report predecessor differs: ' + relative)
        allowed.update(report['authoredFiles'])
    changed = set(subprocess.check_output(['git', 'diff', '--name-only', source_ref, '--',
        'knowledge', 'source/publication'], cwd=root, text=True).splitlines())
    changed.update(subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '--',
        'knowledge', 'source/publication'], cwd=root, text=True).splitlines())
    if changed - allowed:
        raise AssertionError('Unrecognized source changes cannot enter historical inverse: ' + ', '.join(sorted(changed - allowed)))
    baseline_paths = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', source_ref],
        cwd=root, text=True).splitlines())
    records = {}
    for relative in sorted(allowed):
        current = root / relative
        before = subprocess.check_output(['git', 'show', source_ref + ':' + relative], cwd=root) \
            if relative in baseline_paths else None
        if not current.is_file():
            if before is not None:
                raise AssertionError('Source removal is outside the authorized batch inverse: ' + relative)
            continue
        after = current.read_bytes()
        if before == after:
            continue
        records[relative] = {'beforeFileText': None if before is None else before.decode('utf-8'),
            'beforeSha256': None if before is None else sha(before), 'afterSha256': sha(after)}
    return {'schemaVersion': 'official-clause-history-v1', 'asOf': '2026-10-05',
        'baselineCommit': BASELINE, 'baselineTree': TREE,
        'authoredReports': REPORTS, 'metadataPaths': METADATA, 'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--source-ref', default=BASELINE,
        help='Read an equivalent local snapshot only after its tree matches the real remote predecessor')
    parser.add_argument('--out', type=Path, default=Path(__file__).parent / 'fixtures/official_clause_cohort_20261005.json')
    args = parser.parse_args()
    result = freeze(args.root.resolve(), args.source_ref)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(args.out), 'recordCount': len(result['records']),
        'addedPaths': sum(r['beforeFileText'] is None for r in result['records'].values())}))


if __name__ == '__main__':
    main()
