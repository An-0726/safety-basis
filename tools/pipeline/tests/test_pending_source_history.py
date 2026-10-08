"""Pending-source history: immutable predecessors, exact inverse and full chain restoration."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools/browser'), str(ROOT / 'tools/v4')]
import freeze_pending_source_history as FREEZE
from pending_source_cohort_fixture import fixture, pre_pending_repo_root, pre_pending_source_bytes
from complete_remaining_cohort_fixture import pre_complete_repo_root

IMMUTABLE = {
    'tools/browser/fixtures/complete_remaining_20261005.json': '61e47174d62824a524a04460cce24b4d451c932c703371344e4f57b2c0cf283b',
    'tools/browser/fixtures/residual_clauses_20261005.json': 'afd9bb3f623fc677782a22c2a72b2357d3f79b39d4ad85078581d5c81830d032',
    'tools/browser/fixtures/official_clauses_20261005.json': '69501787d0cd5405a5c3ea197d4e122e0c801520f55817d756697c7a06b949bd',
    'tools/browser/fixtures/recovery_release_20261004.json': '56f333aa5accffaca726a17f8fa3d55f9cbaff35ed4a2721a903c39ee67d381d',
    'tools/pipeline/tests/fixtures/complete_remaining_cohort_20261005.json': 'dce0433cb35fe3a111e7157f0c4cd2260487de342a438e93835baf2399d1d72a',
    'tools/pipeline/tests/fixtures/complete_remaining_authorization_20261005.json': 'e6cdbb3b59adaca6fa21c2cce6bbe4812469c652c965f5c4437f828ae7461900',
    'tools/pipeline/tests/fixtures/residual_clause_cohort_20261005.json': '932bf19f529d03c23ede5fb86c46ceb296972ce9bf0ab0886d758c12e16e386d',
    'tools/pipeline/tests/fixtures/official_clause_cohort_20261005.json': 'b6e14b4651a0758844072a0a080cbc047d5724fb58366d1b79f4b3d76b296800',
    'tools/pipeline/tests/fixtures/recovery_cohort_20261004.json': 'b5cc774e369d5bf7cda5770e93c21bd76d97714bbb6d7021f2bb20c7fd37fb95',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class PendingSourceHistoryTests(unittest.TestCase):
    def test_immutable_predecessor_fixtures_and_cohorts_keep_exact_bytes(self):
        self.assertEqual(len(IMMUTABLE), 9)
        for relative, expected in IMMUTABLE.items():
            with self.subTest(path=relative):
                self.assertEqual(sha((ROOT / relative).read_bytes()), expected)

    def test_history_inverse_metadata_matches_frozen_predecessor_and_authorization(self):
        data = fixture()
        self.assertEqual(data['schemaVersion'], 'pending-source-history-v1')
        self.assertEqual(data['asOf'], '2026-10-08')
        self.assertEqual(data['baselineCommit'], FREEZE.BASELINE)
        self.assertEqual(data['baselineTree'], FREEZE.TREE)
        self.assertEqual(data['authoredReports'], FREEZE.REPORTS)
        self.assertEqual(data['authorizationPath'], FREEZE.AUTHORIZATION)
        self.assertEqual(data['metadataPaths'], ['docs/PROJECT_STATE.md', 'knowledge/manifest.json'])
        # BATCH-SPECIFIC: the author report must exist and its SHA must be pinned here once authored.
        for relative, digest in data['authoredReportSha256'].items():
            self.assertEqual(sha((ROOT / relative).read_bytes()), digest, relative)
        self.assertEqual(sha((ROOT / data['authorizationPath']).read_bytes()), data['authorizationSha256'])

    def test_inverse_records_match_final_source_and_exact_git_predecessor(self):
        data = fixture()
        allowed, _ = FREEZE.authorized_hashes(ROOT)
        self.assertLessEqual(set(data['records']), set(allowed))
        # BATCH-SPECIFIC: this batch must record at least one authored change in the inverse.
        self.assertTrue(data['records'])
        for path, row in data['records'].items():
            raw = (ROOT / path).read_bytes()
            self.assertEqual(sha(raw), row['afterSha256'], path)
            self.assertEqual(pre_pending_source_bytes(path, raw),
                             None if row['beforeFileText'] is None else row['beforeFileText'].encode(), path)

    def test_chain_restores_every_older_immutable_browser_snapshot(self):
        from residual_clause_cohort_fixture import pre_residual_repo_root
        from official_clause_cohort_fixture import pre_official_repo_root
        from release_snapshot import source_hashes, snapshot_digest
        for materialize, filename in ((pre_pending_repo_root, 'complete_remaining_20261005.json'),
                                     (pre_complete_repo_root, 'residual_clauses_20261005.json'),
                                     (pre_residual_repo_root, 'official_clauses_20261005.json'),
                                     (pre_official_repo_root, 'recovery_release_20261004.json')):
            with self.subTest(fixture=filename):
                original = json.loads((ROOT / 'tools/browser/fixtures' / filename).read_text(encoding='utf-8'))
                self.assertEqual(snapshot_digest(source_hashes(materialize(ROOT) / 'knowledge')),
                                 original['knowledgeSnapshotHash'])


if __name__ == '__main__':
    unittest.main()
