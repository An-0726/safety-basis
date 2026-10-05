#!/usr/bin/env python3
"""Explicit, author-list-bounded inverse for the residual 2026-10-05 batch.

Never auto-update fixtures in CI. Only the named author manifests and the exact
publication metadata allowlist may contribute paths. Unknown source changes,
removals and a predecessor with a different tree fail closed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASELINE = '23d0e0d415762ccb00341e9e0584c1694f15881d'
TREE = '84ed7015e73ba20ee505541ad94f776be48f31fd'
REPORT_FIELDS = {
    'docs/WAREHOUSE_CANDIDATES_AUTHOR_REVIEW_20261005.json': 'authoredFiles',
    'docs/NEXT_TRAINING_REPAIR_20261005.json': 'authoredFiles',
    'docs/NEXT_AQ7011_AUTHOR_REVIEW_20261005.json': 'ownedPaths',
    'docs/NEXT_BOUNDED_ELECTRICAL_REPAIR_20261005.json': 'authoredFiles',
    'docs/NEXT_INVENTORY_INTEGRATION_20261005.json': 'authoredFiles',
}
METADATA = ['knowledge/manifest.json', 'source/publication/law-index.json',
            'docs/PROJECT_STATE.md']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def authorized_paths(root):
    allowed = set(METADATA)
    for relative, field in REPORT_FIELDS.items():
        report = json.loads((root / relative).read_text(encoding='utf-8'))
        if report.get('baselineCommit') != BASELINE or report.get('baselineTree', TREE) != TREE:
            raise AssertionError('Authored report predecessor differs: ' + relative)
        paths = report.get(field)
        if not isinstance(paths, list) or not paths:
            raise AssertionError('Missing explicit authored path list: ' + relative)
        for path in paths:
            parts = Path(path).parts
            if Path(path).is_absolute() or '..' in parts or not parts:
                raise AssertionError('Out-of-scope authored path: ' + path)
            # Keep author reports and tests as audit records. They are not
            # production-source inverses and cannot remove their own evidence.
            if parts[0] == 'knowledge' or path.startswith('source/publication/'):
                allowed.add(path)
            elif parts[0] not in {'docs', 'tools', 'tests'}:
                raise AssertionError('Out-of-scope authored path: ' + path)
    return allowed


def freeze(root, source_ref=BASELINE):
    root = Path(root)
    tree = subprocess.check_output(['git', 'rev-parse', source_ref + '^{tree}'], cwd=root, text=True).strip()
    if tree != TREE:
        raise AssertionError('Unexpected residual-clause predecessor tree')
    allowed = authorized_paths(root)
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
    return {'schemaVersion': 'residual-clause-history-v1', 'asOf': '2026-10-05',
        'baselineCommit': BASELINE, 'baselineTree': TREE,
        'authoredReports': list(REPORT_FIELDS), 'authoredReportFields': REPORT_FIELDS,
        'metadataPaths': METADATA, 'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--source-ref', default=BASELINE,
        help='Read an equivalent local snapshot only after verifying the real remote predecessor tree')
    parser.add_argument('--out', type=Path, default=Path(__file__).parent / 'fixtures/residual_clause_cohort_20261005.json')
    args = parser.parse_args()
    result = freeze(args.root.resolve(), args.source_ref)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(args.out), 'recordCount': len(result['records']),
        'addedPaths': sum(r['beforeFileText'] is None for r in result['records'].values())}))


if __name__ == '__main__':
    main()
