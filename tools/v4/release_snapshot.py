"""Capture one stable knowledge input for all release readers, without source writes."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

FORMAL_NAMESPACES = ('hazards', 'links', 'clauses', 'law-versions', 'laws', 'evidence',
                     'reviews', 'field-profiles/v1/records', 'field-profiles/v1/reviews',
                     'major-criteria/v1', 'major-criteria-references/v1', 'major-criteria-directory/v1',
                     'major-criteria-reading/v1')


def source_hashes(root, *, include_pilot=False):
    root = Path(root)
    paths = [root / 'manifest.json'] if (root / 'manifest.json').exists() else []
    namespaces = FORMAL_NAMESPACES + (('field-profiles-pilot',) if include_pilot else ())
    for namespace in namespaces:
        paths.extend((root / namespace).rglob('*.json'))
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(set(paths))}


def snapshot_digest(hashes):
    return hashlib.sha256(json.dumps(sorted(hashes.items()), ensure_ascii=False,
                                     separators=(',', ':')).encode('utf-8')).hexdigest()


@contextmanager
def stable_knowledge_snapshot(knowledge, *, include_pilot=False):
    """Abort if source changed during capture; consumers only read the private copy.

    This detects mutation during capture, not malicious change-and-revert races.
    Authoring must still be quiescent while a snapshot is captured.
    """
    source = Path(knowledge)
    before = source_hashes(source, include_pilot=include_pilot)
    with tempfile.TemporaryDirectory(prefix='safety-release-knowledge-') as temp:
        snapshot = Path(temp)
        for rel in before:
            target = snapshot / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / rel, target)
        if (source_hashes(snapshot, include_pilot=include_pilot) != before or
                source_hashes(source, include_pilot=include_pilot) != before):
            raise ValueError('knowledge changed during release snapshot capture; retry after authoring stops')
        yield snapshot, snapshot_digest(before)
