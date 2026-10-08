"""Exact, test-only inverse preceding residual -> official -> recovery history.

Unknown changes survive materialization. Recorded bytes must match exactly,
including on cache hits; only approved additions can disappear in this view.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from pending_source_cohort_fixture import pre_pending_repo_root

FIXTURE = Path(__file__).parent / 'fixtures/complete_remaining_cohort_20261005.json'
_SNAPSHOTS = {}
_PREDECESSOR_ROOTS = set()


def fixture():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def pre_complete_source_bytes(path, raw, *, records=None):
    records = fixture()['records'] if records is None else records
    row = records.get(path)
    if row is None:
        return raw
    if hashlib.sha256(raw).hexdigest() != row['afterSha256']:
        raise AssertionError('unexpected complete-batch source change: ' + path)
    if row['beforeFileText'] is None:
        if row['beforeSha256'] is not None:
            raise AssertionError('corrupt complete-batch addition: ' + path)
        return None
    before = row['beforeFileText'].encode('utf-8')
    if hashlib.sha256(before).hexdigest() != row['beforeSha256']:
        raise AssertionError('corrupt complete-batch predecessor: ' + path)
    return before


def restore_complete_paths(root, destination, *, records):
    root, destination = Path(root), Path(destination)
    for relative in records:
        p = PurePosixPath(relative)
        if (p.is_absolute() or '..' in p.parts or '\\' in relative or str(p) != relative
                or not relative.startswith(('knowledge/', 'docs/', 'source/publication/'))):
            raise AssertionError('out-of-scope complete-batch path: ' + relative)
        before = pre_complete_source_bytes(relative, (root / relative).read_bytes(), records=records)
        target = destination / relative
        if before is None:
            target.unlink()
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(before)


def pre_complete_repo_root(root):
    root = Path(root).resolve()
    if root in _PREDECESSOR_ROOTS:
        return root
    root = pre_pending_repo_root(root)
    records = fixture()['records']
    for relative in records:
        pre_complete_source_bytes(relative, (root / relative).read_bytes(), records=records)
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
    owner = tempfile.TemporaryDirectory(prefix='safety-complete-history-')
    snapshot = Path(owner.name)
    for child in root.iterdir():
        if child.name == '.git':
            continue
        target = snapshot / child.name
        if child.name in {'knowledge', 'docs', 'source'}:
            shutil.copytree(child, target, ignore=shutil.ignore_patterns('releases', 'library'))
        else:
            target.symlink_to(child, target_is_directory=child.is_dir())
    restore_complete_paths(root, snapshot, records=records)
    _SNAPSHOTS[key] = (owner, snapshot)
    _PREDECESSOR_ROOTS.add(snapshot)
    return snapshot
