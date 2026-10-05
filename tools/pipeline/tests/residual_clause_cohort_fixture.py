"""Exact test-only predecessor for the 2026-10-05 residual-clause batch.

Only explicitly recorded batch paths are reversed, after exact current-byte
validation. Unknown additions and unrelated changes remain visible. This helper
never changes production knowledge, review decisions, Gate code or old fixtures.
"""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

FIXTURE = Path(__file__).parent / 'fixtures/residual_clause_cohort_20261005.json'
_SNAPSHOTS = {}
_PREDECESSOR_ROOTS = set()


def fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def pre_residual_source_bytes(path, raw, *, records=None):
    records = fixture()['records'] if records is None else records
    row = records.get(path)
    if row is None:
        return raw
    if hashlib.sha256(raw).hexdigest() != row['afterSha256']:
        raise AssertionError('unexpected residual-clause source change: ' + path)
    if row['beforeFileText'] is None:
        if row['beforeSha256'] is not None:
            raise AssertionError('corrupt residual-clause addition: ' + path)
        return None
    before = row['beforeFileText'].encode('utf-8')
    if hashlib.sha256(before).hexdigest() != row['beforeSha256']:
        raise AssertionError('corrupt residual-clause predecessor: ' + path)
    return before


def restore_residual_paths(root, destination, *, records):
    """Restore an explicitly supplied record set; no wildcard delta inference."""
    root, destination = Path(root), Path(destination)
    for relative, row in records.items():
        parts = Path(relative).parts
        if Path(relative).is_absolute() or '..' in parts or not parts or parts[0] not in {'knowledge', 'docs', 'source'}:
            raise AssertionError('out-of-scope residual-clause path: ' + relative)
        before = pre_residual_source_bytes(relative, (root / relative).read_bytes(), records=records)
        target = destination / relative
        if before is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(before)


def pre_residual_repo_root(root):
    """Create a guarded predecessor; unknown paths are copied without filtering."""
    root = Path(root).resolve()
    if root in _PREDECESSOR_ROOTS:
        return root
    records = fixture()['records']
    # Validate even on cache hits. A later source edit cannot reuse a stale view.
    for relative in records:
        pre_residual_source_bytes(relative, (root / relative).read_bytes(), records=records)
    # Include unknown additions/mutations in cache identity; they must remain
    # observable even if a previous historical view was already materialized.
    state = hashlib.sha256()
    for name in ('knowledge', 'docs', 'source'):
        for path in sorted((root / name).rglob('*')):
            if not path.is_file() or {'releases', 'library'} & set(path.relative_to(root).parts):
                continue
            state.update(path.relative_to(root).as_posix().encode())
            state.update(b'\0')
            state.update(hashlib.sha256(path.read_bytes()).digest())
    key = (root, state.hexdigest())
    if key in _SNAPSHOTS:
        return _SNAPSHOTS[key][1]
    owner = tempfile.TemporaryDirectory(prefix='safety-residual-history-')
    snapshot = Path(owner.name)
    for child in root.iterdir():
        if child.name == '.git':
            continue
        target = snapshot / child.name
        if child.name in {'knowledge', 'docs', 'source'}:
            shutil.copytree(child, target, ignore=shutil.ignore_patterns('releases', 'library'))
        else:
            target.symlink_to(child, target_is_directory=child.is_dir())
    restore_residual_paths(root, snapshot, records=records)
    _SNAPSHOTS[key] = (owner, snapshot)
    _PREDECESSOR_ROOTS.add(snapshot)
    return snapshot
