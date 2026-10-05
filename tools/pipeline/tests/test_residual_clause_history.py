"""Exact residual inverse, immutable legacy bytes and fail-closed composition."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import freeze_residual_clause_history as FREEZE
from residual_clause_cohort_fixture import (
    fixture, pre_residual_repo_root, pre_residual_source_bytes, restore_residual_paths,
)

ROOT = Path(__file__).resolve().parents[3]
from complete_remaining_cohort_fixture import pre_complete_repo_root
ROOT = pre_complete_repo_root(ROOT)
sys.path.insert(0, str(ROOT / 'tools/v4'))
from release_snapshot import source_hashes, snapshot_digest


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def record(before, after):
    return {'beforeFileText': None if before is None else before.decode(),
            'beforeSha256': None if before is None else sha(before), 'afterSha256': sha(after)}


class ResidualClauseHistoryTests(unittest.TestCase):
    def test_current_batch_bytes_are_exact_and_only_authorized_paths_are_reversed(self):
        data = fixture()
        self.assertEqual(data['baselineCommit'], '23d0e0d415762ccb00341e9e0584c1694f15881d')
        self.assertEqual(data['baselineTree'], '84ed7015e73ba20ee505541ad94f776be48f31fd')
        self.assertEqual(data['authoredReportFields'], FREEZE.REPORT_FIELDS)
        self.assertEqual(data['metadataPaths'], FREEZE.METADATA)
        self.assertTrue(data['records'])
        self.assertLessEqual(set(data['records']), FREEZE.authorized_paths(ROOT))
        for relative, row in data['records'].items():
            with self.subTest(path=relative):
                current = (ROOT / relative).read_bytes()
                self.assertEqual(sha(current), row['afterSha256'])
                self.assertEqual(pre_residual_source_bytes(relative, current),
                    None if row['beforeFileText'] is None else row['beforeFileText'].encode())
                with self.assertRaises(AssertionError):
                    pre_residual_source_bytes(relative, current + b' ')

    def test_exact_historical_source_restores_official_then_recovery_without_new_goldens(self):
        from official_clause_cohort_fixture import pre_official_repo_root
        prior = pre_residual_repo_root(ROOT)
        official = json.loads((ROOT / 'tools/browser/fixtures/official_clauses_20261005.json').read_text())
        recovery = json.loads((ROOT / 'tools/browser/fixtures/recovery_release_20261004.json').read_text())
        self.assertEqual(snapshot_digest(source_hashes(prior / 'knowledge')), official['knowledgeSnapshotHash'])
        self.assertEqual(snapshot_digest(source_hashes(pre_official_repo_root(ROOT) / 'knowledge')),
                         recovery['knowledgeSnapshotHash'])
        self.assertEqual(pre_residual_repo_root(prior), prior)
        self.assertEqual(pre_official_repo_root(prior), pre_official_repo_root(ROOT))

    def test_previous_official_fixtures_remain_byte_identical(self):
        for relative, expected in {
            'tools/browser/fixtures/official_clauses_20261005.json': '69501787d0cd5405a5c3ea197d4e122e0c801520f55817d756697c7a06b949bd',
            'tools/pipeline/tests/fixtures/official_clause_cohort_20261005.json': 'b6e14b4651a0758844072a0a080cbc047d5724fb58366d1b79f4b3d76b296800',
        }.items():
            self.assertEqual(sha((ROOT / relative).read_bytes()), expected)

    def test_unknown_bytes_remain_visible_and_corrupt_or_stale_records_fail(self):
        self.assertEqual(pre_residual_source_bytes('knowledge/unknown.json', b'changed', records={}), b'changed')
        path = 'knowledge/hazards/H_TEST.json'
        rows = {path: record(b'old', b'new')}
        self.assertEqual(pre_residual_source_bytes(path, b'new', records=rows), b'old')
        for mutate in ('before_text', 'before_hash', 'after_hash'):
            bad = copy.deepcopy(rows)
            if mutate == 'before_text': bad[path]['beforeFileText'] = 'wrong'
            elif mutate == 'before_hash': bad[path]['beforeSha256'] = '0' * 64
            else: bad[path]['afterSha256'] = '0' * 64
            with self.subTest(mutation=mutate), self.assertRaises(AssertionError):
                pre_residual_source_bytes(path, b'new', records=bad)
        bad = {path: record(None, b'new')}; bad[path]['beforeSha256'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'corrupt'):
            pre_residual_source_bytes(path, b'new', records=bad)
        with self.assertRaisesRegex(AssertionError, 'unexpected'):
            pre_residual_source_bytes(path, b'old', records=rows)

    def test_unknown_additions_mutations_and_deletions_survive_cache_materialization(self):
        path = 'knowledge/hazards/H_TEST.json'
        rows = {path: record(b'old', b'new')}
        with tempfile.TemporaryDirectory() as tmp, patch('residual_clause_cohort_fixture.fixture', return_value={'records': rows}), patch('residual_clause_cohort_fixture.pre_complete_repo_root', side_effect=lambda root: root):
            root = Path(tmp)
            (root / path).parent.mkdir(parents=True)
            (root / path).write_bytes(b'new')
            for name in ('docs', 'source'): (root / name).mkdir()
            unknown = root / 'knowledge/hazards/H_UNKNOWN.json'
            unknown.write_bytes(b'unknown')
            first = pre_residual_repo_root(root)
            self.assertEqual((first / path).read_bytes(), b'old')
            self.assertEqual((first / unknown.relative_to(root)).read_bytes(), b'unknown')
            unknown.write_bytes(b'changed after cache')
            second = pre_residual_repo_root(root)
            self.assertNotEqual(first, second)
            self.assertEqual((second / unknown.relative_to(root)).read_bytes(), b'changed after cache')
            unknown.unlink()
            third = pre_residual_repo_root(root)
            self.assertNotEqual(second, third)
            self.assertFalse((third / unknown.relative_to(root)).exists())
            added = root / 'knowledge/new_unknown.json'; added.write_bytes(b'new unknown')
            self.assertEqual((pre_residual_repo_root(root) / added.relative_to(root)).read_bytes(), b'new unknown')
            (root / path).write_bytes(b'unrecognized drift')
            with self.assertRaisesRegex(AssertionError, 'unexpected'): pre_residual_repo_root(root)
            (root / path).unlink()
            with self.assertRaises(FileNotFoundError): pre_residual_repo_root(root)

    def test_only_pinned_additions_are_removed_and_paths_are_bounded(self):
        path = 'knowledge/hazards/H_ADDED.json'
        rows = {path: record(None, b'new')}
        with tempfile.TemporaryDirectory() as tmp:
            root, target = Path(tmp) / 'current', Path(tmp) / 'prior'
            (root / path).parent.mkdir(parents=True)
            (root / path).write_bytes(b'new')
            shutil.copytree(root, target)
            restore_residual_paths(root, target, records=rows)
            self.assertFalse((target / path).exists())
            self.assertEqual((root / path).read_bytes(), b'new')
            for bad in ('../elsewhere.json', '/tmp/elsewhere.json', 'web/app.js'):
                with self.assertRaisesRegex(AssertionError, 'out-of-scope'):
                    restore_residual_paths(root, target, records={bad: record(None, b'new')})

    def test_freezer_rejects_unknown_changes_removals_and_wrong_predecessor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
            git('init', '-q')
            p = root / 'knowledge/hazards/H_TEST.json'; p.parent.mkdir(parents=True); p.write_text('old')
            git('add', '.')
            git('-c', 'user.name=Fixture Test', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'baseline')
            commit, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
            report = root / 'docs/author.json'; report.parent.mkdir()
            report.write_text(json.dumps({'baselineCommit': commit, 'authoredFiles': ['knowledge/hazards/H_TEST.json']}))
            with patch.multiple(FREEZE, BASELINE=commit, TREE=tree, REPORT_FIELDS={'docs/author.json': 'authoredFiles'}, METADATA=[]):
                p.write_text('new')
                frozen = FREEZE.freeze(root, commit)
                self.assertEqual(frozen['records'], {'knowledge/hazards/H_TEST.json': record(b'old', b'new')})
                unknown = root / 'knowledge/unknown.json'; unknown.write_text('unknown')
                with self.assertRaisesRegex(AssertionError, 'Unrecognized source changes'): FREEZE.freeze(root, commit)
                unknown.unlink(); p.unlink()
                with self.assertRaisesRegex(AssertionError, 'Source removal'): FREEZE.freeze(root, commit)
                p.write_text('new')
                with patch.object(FREEZE, 'TREE', '0' * 40), self.assertRaisesRegex(AssertionError, 'predecessor tree'):
                    FREEZE.freeze(root, commit)
                report.write_text(json.dumps({'baselineCommit': 'wrong', 'authoredFiles': ['knowledge/hazards/H_TEST.json']}))
                with self.assertRaisesRegex(AssertionError, 'report predecessor'): FREEZE.freeze(root, commit)


if __name__ == '__main__':
    unittest.main()
