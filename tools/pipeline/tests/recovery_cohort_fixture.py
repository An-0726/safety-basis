"""Pinned test-only inverse of the independently re-reviewed recovery cohort.

This is never loaded by production code. Historical assertions retain their
original expected values; a separate current-cohort test pins every new byte.
Unknown additions and unrelated changes remain visible to the old assertions.
"""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from official_clause_cohort_fixture import pre_official_repo_root

F = json.loads((Path(__file__).parent / 'fixtures/recovery_cohort_20261004.json').read_text())
_SNAPSHOTS = {}


def pre_recovery_repo_root(root, *, keep_paths=()):
    """Materialize a guarded predecessor for historical cohort assertions.

    Only explicitly pinned recovery paths are reversed. Unknown mutations remain
    in the copy and are visible to the original tests. Production source and
    Gate are never patched. Current-cohort tests separately require new bytes.
    """
    root = pre_official_repo_root(root)
    keep_paths = frozenset(keep_paths)
    key = (str(root), tuple(sorted(keep_paths)))
    if key in _SNAPSHOTS:
        return _SNAPSHOTS[key][1]
    owner = tempfile.TemporaryDirectory(prefix='safety-historical-test-')
    snapshot = Path(owner.name)
    mutable_roots = {'knowledge', 'docs', 'source'}
    for child in root.iterdir():
        if child.name == '.git':
            continue
        target = snapshot / child.name
        if child.name in mutable_roots:
            shutil.copytree(child, target, ignore=shutil.ignore_patterns('releases', 'library'))
        else:
            target.symlink_to(child, target_is_directory=child.is_dir())
    for relative, row in F['records'].items():
        raw = (root / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['afterSha256']:
            raise AssertionError('current recovery source drift before historical materialization: ' + relative)
        if relative in keep_paths:
            continue
        path = snapshot / relative
        if row['beforeFileText'] is None:
            path.unlink()
        else:
            before = row['beforeFileText'].encode()
            if hashlib.sha256(before).hexdigest() != row['beforeSha256']:
                raise AssertionError('corrupt recovery predecessor: ' + relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(before)
    _SNAPSHOTS[key] = (owner, snapshot)
    return snapshot


def evaluate_historical_snapshot(*args, **kwargs):
    """Evaluate a materialized predecessor with unchanged production Gate code."""
    from release_gate_core import evaluate_release_gate
    result = evaluate_release_gate(*args, **kwargs)
    result._recovery_before_projected = True
    return result


def pre_recovery_source_bytes(path, raw):
    row = F['records'].get(path)
    if row is None:
        return raw
    digest = hashlib.sha256(raw).hexdigest()
    # Exact predecessor bytes can occur when historical helper layers compose.
    # Current source bytes are independently pinned by the cohort's own tests.
    if row['beforeSha256'] and digest == row['beforeSha256']:
        return raw
    if digest != row['afterSha256']:
        raise AssertionError('unexpected recovery source change: ' + path)
    if row['beforeFileText'] is None:
        return None
    before = row['beforeFileText'].encode()
    if hashlib.sha256(before).hexdigest() != row['beforeSha256']:
        raise AssertionError('corrupt recovery historical source: ' + path)
    return before


def pre_recovery_ids(kind, ids):
    return set(ids) - set(F['addedIds'].get(kind, []))


def pre_recovery_inventory(kind, rows):
    result = []
    for ident, state in rows:
        if ident in F['addedIds'].get(kind, []):
            continue
        row = F['lifecycleChanges'].get(kind, {}).get(ident)
        if row:
            if state not in (row['before'], row['after']):
                raise AssertionError('unexpected recovery lifecycle change: ' + ident)
            state = row['before']
        result.append((ident, state))
    return result


def pre_recovery_manifest(manifest):
    prior = copy.deepcopy(manifest)
    receipts = F['manifestAddedReceipts']
    present = {r.get('id') for r in prior.get('batches', [])}
    expected = {r['id'] for r in receipts}
    if expected and not expected & present:
        return prior  # Historical or unrelated synthetic manifest.
    if not expected <= present:
        raise AssertionError('partial recovery manifest receipt set')
    for receipt in F['manifestAddedReceipts']:
        rows = [r for r in prior.get('batches', []) if r.get('id') == receipt['id']]
        if rows != [receipt]:
            raise AssertionError('recovery manifest receipt drift')
        prior['batches'].remove(receipt)
    for section in ('counts', 'lifecycle'):
        for key, delta in F['manifestNumericDelta'].get(section, {}).items():
            prior[section][key] -= delta
    for key, delta in F['manifestNumericDelta'].get('root', {}).items():
        prior[key] -= delta
    for key, change in F['manifestMetadataChanges'].items():
        if prior.get(key) == change['after']:
            prior[key] = copy.deepcopy(change['before'])
    return prior


def pre_recovery_gate(gate):
    prior = copy.deepcopy(gate)
    if getattr(gate, '_recovery_before_projected', False):
        return prior
    delta = F['gateSnapshots'].get(str(getattr(gate, 'as_of', '')))
    if delta is None:
        return prior
    changed_ids = {ident for rows in delta['judgments'].values() for ident in rows}
    current_ids = set(gate.links) | set(getattr(gate, 'hazards', {}))
    if changed_ids and not changed_ids & current_ids:
        return prior  # A wholly unrelated synthetic Gate object.
    for kind, rows in delta['judgments'].items():
        current = getattr(gate, kind, {})
        target = getattr(prior, kind, {})
        for ident, row in rows.items():
            if current.get(ident) != row['after']:
                raise AssertionError('recovery Gate judgment drift: ' + ident)
            if row['before'] is None:
                target.pop(ident, None)
            else:
                target[ident] = copy.deepcopy(row['before'])
    for attr, added, removed in (
        ('eligible_hazards', 'hazardsAdded', 'hazardsRemoved'),
        ('eligible_links', 'linksAdded', 'linksRemoved'),
    ):
        values = set(getattr(gate, attr))
        if not set(delta[added]) <= values or set(delta[removed]) & values:
            raise AssertionError('recovery Gate membership drift: ' + attr)
        setattr(prior, attr, (values - set(delta[added])) | set(delta[removed]))
    prior._recovery_before_projected = True
    return prior
