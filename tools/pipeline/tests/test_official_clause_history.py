"""Auditable batch-only inverses preserve old assertions and expose unknown drift."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from official_clause_cohort_fixture import (
    fixture, pre_official_repo_root, pre_official_source_bytes, restore_official_paths,
)

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from release_snapshot import source_hashes, snapshot_digest


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def record(before, after):
    return {'beforeFileText': None if before is None else before.decode(),
            'beforeSha256': None if before is None else sha(before),
            'afterSha256': sha(after)}


class OfficialClauseHistoryTests(unittest.TestCase):
    def test_current_batch_bytes_and_recoverable_predecessor_are_exact(self):
        data = fixture()
        self.assertEqual(data['baselineCommit'], '792d0c9c0ee553e8e0a0312a9a190d82baccf4d1')
        self.assertEqual(data['baselineTree'], '3867f248ac7cc7e7e660db404bb0dc2c6bd1d62a')
        self.assertTrue(data['records'])
        allowed = set(data['metadataPaths'])
        for report in data['authoredReports']:
            allowed.update(json.loads((ROOT / report).read_text())['authoredFiles'])
        self.assertLessEqual(set(data['records']), allowed)
        for relative, row in data['records'].items():
            with self.subTest(path=relative):
                current = (ROOT / relative).read_bytes()
                self.assertEqual(sha(current), row['afterSha256'])
                old = pre_official_source_bytes(relative, current)
                self.assertEqual(old, None if row['beforeFileText'] is None else row['beforeFileText'].encode())
                with self.assertRaises(AssertionError):
                    pre_official_source_bytes(relative, current + b' ')
        prior = pre_official_repo_root(ROOT)
        legacy = json.loads((ROOT / 'tools/browser/fixtures/recovery_release_20261004.json').read_text())
        self.assertEqual(snapshot_digest(source_hashes(prior / 'knowledge')), legacy['knowledgeSnapshotHash'])

    def test_unknown_bytes_are_visible_and_corrupt_predecessors_fail(self):
        self.assertEqual(pre_official_source_bytes('knowledge/unknown.json', b'changed', records={}), b'changed')
        path = 'knowledge/hazards/H_TEST.json'
        rows = {path: record(b'old', b'new')}
        self.assertEqual(pre_official_source_bytes(path, b'new', records=rows), b'old')
        bad = copy.deepcopy(rows); bad[path]['beforeFileText'] = 'wrong'
        with self.assertRaisesRegex(AssertionError, 'corrupt'):
            pre_official_source_bytes(path, b'new', records=bad)
        bad = {path: record(None, b'new')}; bad[path]['beforeSha256'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'corrupt'):
            pre_official_source_bytes(path, b'new', records=bad)
        with self.assertRaisesRegex(AssertionError, 'unexpected'):
            pre_official_source_bytes(path, b'old', records=rows)

    def test_materialization_preserves_unknown_changes_even_after_cache(self):
        path = 'knowledge/hazards/H_TEST.json'
        rows = {path: record(b'old', b'new')}
        with tempfile.TemporaryDirectory() as tmp, patch('official_clause_cohort_fixture.fixture', return_value={'records': rows}):
            root = Path(tmp)
            (root / path).parent.mkdir(parents=True)
            (root / path).write_bytes(b'new')
            unknown = root / 'knowledge/hazards/H_UNKNOWN.json'
            unknown.write_bytes(b'unknown')
            for name in ('docs', 'source'):
                (root / name).mkdir()
            before = pre_official_repo_root(root)
            self.assertEqual((before / path).read_bytes(), b'old')
            self.assertEqual((before / unknown.relative_to(root)).read_bytes(), b'unknown')
            unknown.write_bytes(b'changed after cache')
            after = pre_official_repo_root(root)
            self.assertNotEqual(before, after)
            self.assertEqual((after / unknown.relative_to(root)).read_bytes(), b'changed after cache')
            (root / path).write_bytes(b'unrecognized drift')
            with self.assertRaisesRegex(AssertionError, 'unexpected'):
                pre_official_repo_root(root)

    def test_additions_are_removed_only_with_exact_current_pin_and_paths_are_bounded(self):
        path = 'knowledge/hazards/H_ADDED.json'
        rows = {path: record(None, b'new')}
        with tempfile.TemporaryDirectory() as tmp:
            root, target = Path(tmp) / 'current', Path(tmp) / 'prior'
            (root / path).parent.mkdir(parents=True)
            (root / path).write_bytes(b'new')
            shutil.copytree(root, target)
            restore_official_paths(root, target, records=rows)
            self.assertFalse((target / path).exists())
            self.assertEqual((root / path).read_bytes(), b'new')
            for bad in ('../elsewhere.json', '/tmp/elsewhere.json', 'web/app.js'):
                with self.assertRaisesRegex(AssertionError, 'out-of-scope'):
                    restore_official_paths(root, target, records={bad: record(None, b'new')})


if __name__ == '__main__':
    unittest.main()
