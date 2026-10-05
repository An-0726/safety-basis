#!/usr/bin/env python3
"""Freeze an explicitly authorized, hash-checked inverse of the complete batch.

This is a manual, reviewed operation, never an expectation updater in CI. Author
lists and the separately approved exact metadata list bound the inverse. Git
supplies original bytes; neither generated releases nor reports supply them.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
BASELINE = '475856179bfd3c6c3446d10cfc4de73e51f228f3'
LOCAL_BASELINE = 'a40d8d961a53b5379916a67b522801088390c974'
TREE = 'fc62800c09421f687c0734f699b95befa8231f2f'
REPORTS = [
    'docs/all-electrical-bounded-author-20261005.json',
    'docs/COMPLETE_REMAINING_FIRE_GAS_AUTHOR_20261005.json',
    'docs/complete-equipment-author-20261005.json',
    'docs/all-management-bounded-author-20261005.json',
    'docs/COMPLETE_REMAINING_CENTRAL_INTEGRATION_20261005.json',
]
AUTHORIZATION = 'tools/pipeline/tests/fixtures/complete_remaining_authorization_20261005.json'
FIXTURE = 'tools/pipeline/tests/fixtures/complete_remaining_cohort_20261005.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_path(relative):
    if not isinstance(relative, str):
        raise AssertionError('Non-string authored path')
    parts = PurePosixPath(relative).parts
    if (not parts or PurePosixPath(relative).is_absolute() or '..' in parts or '\\' in relative
            or str(PurePosixPath(relative)) != relative):
        raise AssertionError('Out-of-scope authored path: ' + relative)
    return relative


def is_source(relative):
    return relative.startswith(('knowledge/', 'source/publication/'))


def checked_sha(value, label):
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise AssertionError('Missing or invalid authored SHA256: ' + label)
    return value


def report_hashes(report):
    """Normalize the observed author schemas without inventing current hashes."""
    result = dict(report.get('authoredSha256', {}))
    for row in report.get('fileHashes', []):
        path = checked_path(row['path'])
        digest = row.get('afterSha256')
        if path in result and result[path] != digest:
            raise AssertionError('Conflicting author hashes: ' + path)
        result[path] = digest
    for row in report.get('authoredFiles', []):
        if isinstance(row, dict):
            path = checked_path(row['path'])
            digest = row.get('sha256', row.get('afterSha256'))
            if path in result and result[path] != digest:
                raise AssertionError('Conflicting author hashes: ' + path)
            result[path] = digest
    return result


def load_authorization(root):
    data = json.loads((Path(root) / AUTHORIZATION).read_text(encoding='utf-8'))
    if data.get('baselineCommit') != BASELINE or data.get('baselineTree') != TREE:
        raise AssertionError('Authorization predecessor differs')
    paths = data.get('metadataPaths')
    if not isinstance(paths, list) or paths != sorted(set(paths)):
        raise AssertionError('Metadata authorization must be an explicit sorted unique list')
    for relative in paths:
        checked_path(relative)
        if not (is_source(relative) or relative.startswith('docs/')):
            raise AssertionError('Out-of-scope metadata path: ' + relative)
    withdrawals = data.get('withdrawals')
    if not isinstance(withdrawals, dict) or set(withdrawals) != {'hazards', 'links'}:
        raise AssertionError('Explicit hazard/link withdrawal authorization required')
    for kind, prefix in (('hazards', 'H'), ('links', 'K')):
        rows = withdrawals[kind]
        if not isinstance(rows, dict) or any(not k.startswith(prefix) or not isinstance(v, str) or not v.strip() for k, v in rows.items()):
            raise AssertionError('Withdrawal IDs need individual reviewed reasons: ' + kind)
    return data


def authorized_hashes(root, authorization=None):
    root = Path(root)
    authorization = load_authorization(root) if authorization is None else authorization
    allowed, before_claims = {}, {}
    for relative in REPORTS:
        report = json.loads((root / relative).read_text(encoding='utf-8'))
        if report.get('baselineCommit') != BASELINE or report.get('baselineTree') != TREE:
            raise AssertionError('Authored report predecessor differs: ' + relative)
        rows = report.get('authoredFiles')
        if not isinstance(rows, list) or not rows:
            raise AssertionError('Missing explicit authored path list: ' + relative)
        paths = [checked_path(row['path'] if isinstance(row, dict) else row) for row in rows]
        if len(paths) != len(set(paths)):
            raise AssertionError('Duplicate authored path: ' + relative)
        hashes = report_hashes(report)
        for path in paths:
            if not is_source(path) and path not in authorization['metadataPaths']:
                if not path.startswith(('docs/', 'tools/', 'tests/')):
                    raise AssertionError('Out-of-scope authored path: ' + path)
                continue
            digest = checked_sha(hashes.get(path), path)
            if path in allowed and allowed[path] != digest:
                raise AssertionError('Conflicting shared source ownership: ' + path)
            allowed[path] = digest
        claims = {p: row.get('sha256', row.get('beforeSha256')) for p, row in report.get('beforeFiles', {}).items()}
        claims.update({p: row.get('sha256') for p, row in report.get('beforeFileHashes', {}).items()})
        claims.update({row['path']: row.get('beforeSha256') for row in report.get('fileHashes', [])})
        for path, digest in claims.items():
            if path not in paths or not (is_source(path) or path in authorization['metadataPaths']):
                continue
            if path in before_claims and before_claims[path] != digest:
                raise AssertionError('Conflicting predecessor claims: ' + path)
            before_claims[path] = digest
    # Metadata hashes are frozen from the approved, bounded list only. They are
    # validated on every use of the resulting immutable fixture.
    for path in authorization['metadataPaths']:
        # A central authored hash remains mandatory even when the same exact
        # metadata path is also approved. The metadata list never weakens it.
        allowed.setdefault(path, None)
    return allowed, before_claims


def current_source_state(root, metadata_paths):
    state = {}
    for directory in ('knowledge', 'source/publication'):
        for path in (root / directory).rglob('*'):
            if path.is_symlink():
                raise AssertionError('Source symlink is not auditable: ' + str(path))
            if path.is_file():
                state[path.relative_to(root).as_posix()] = sha(path.read_bytes())
    for relative in metadata_paths:
        path = root / relative
        if path.is_symlink():
            raise AssertionError('Metadata symlink is not auditable: ' + relative)
        state[relative] = sha(path.read_bytes()) if path.is_file() else None
    return state


def freeze(root, source_ref=LOCAL_BASELINE):
    root = Path(root).resolve()
    resolved = subprocess.check_output(['git', 'rev-parse', source_ref + '^{commit}'], cwd=root, text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', resolved + '^{tree}'], cwd=root, text=True).strip()
    if tree != TREE:
        raise AssertionError('Unexpected complete-batch predecessor tree')
    audit_pins = {p: sha((root / p).read_bytes()) for p in [*REPORTS, AUTHORIZATION]}
    authorization = load_authorization(root)
    initial_source_state = current_source_state(root, authorization['metadataPaths'])
    allowed, before_claims = authorized_hashes(root, authorization)
    baseline_paths = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', resolved], cwd=root, text=True).splitlines())
    source_paths = {p for p in baseline_paths if is_source(p)}
    for directory in ('knowledge', 'source/publication'):
        for path in (root / directory).rglob('*'):
            if path.is_symlink():
                raise AssertionError('Source symlink is not auditable: ' + str(path))
            if path.is_file():
                source_paths.add(path.relative_to(root).as_posix())
    # One immutable Git archive provides all original bytes, including exact
    # line endings, without thousands of individual subprocesses.
    archive_raw = subprocess.check_output(['git', 'archive', resolved], cwd=root)
    with tarfile.open(fileobj=io.BytesIO(archive_raw)) as archive:
        baseline_bytes = {member.name: archive.extractfile(member).read() for member in archive.getmembers()
                          if member.isfile() and (is_source(member.name) or member.name in allowed)}
    records = {}
    for relative in sorted(source_paths | set(allowed)):
        checked_path(relative)
        current = root / relative
        before = baseline_bytes.get(relative)
        if current.is_symlink():
            raise AssertionError('Source symlink is not auditable: ' + relative)
        after = current.read_bytes() if current.is_file() else None
        if relative in allowed:
            if after is None:
                raise AssertionError('Source removal is outside the authorized batch inverse: ' + relative)
            if allowed[relative] is not None and sha(after) != allowed[relative]:
                raise AssertionError('Authored source hash drift: ' + relative)
            if relative in before_claims and before_claims[relative] != (sha(before) if before is not None else None):
                raise AssertionError('Authored predecessor hash differs from Git: ' + relative)
        if before == after:
            continue
        if relative not in allowed:
            raise AssertionError('Unrecognized source changes cannot enter historical inverse: ' + relative)
        records[relative] = {'beforeFileText': None if before is None else before.decode('utf-8'),
            'beforeSha256': None if before is None else sha(before), 'afterSha256': sha(after)}
    if initial_source_state != current_source_state(root, authorization['metadataPaths']):
        raise AssertionError('Source changed during complete-batch freeze')
    if any(sha((root / p).read_bytes()) != digest for p, digest in audit_pins.items()):
        raise AssertionError('Author or authorization changed during complete-batch freeze')
    return {'schemaVersion': 'complete-remaining-history-v1', 'asOf': '2026-10-05',
        'baselineCommit': BASELINE, 'baselineTree': TREE,
        'authoredReports': REPORTS, 'authoredReportSha256': {p: audit_pins[p] for p in REPORTS},
        'authorizationPath': AUTHORIZATION, 'authorizationSha256': audit_pins[AUTHORIZATION],
        'metadataPaths': authorization['metadataPaths'], 'records': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--source-ref', default=LOCAL_BASELINE)
    parser.add_argument('--out', type=Path, default=ROOT / FIXTURE)
    args = parser.parse_args()
    result = freeze(args.root, args.source_ref)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'path': str(args.out), 'recordCount': len(result['records'])}))


if __name__ == '__main__':
    main()
