"""Fail-closed author scope, byte inverses and exact withdrawal mutation tests."""
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

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools/browser'), str(ROOT / 'tools/v4')]
import freeze_complete_remaining_history as FREEZE
from complete_remaining_cohort_fixture import (fixture, pre_complete_repo_root,
    pre_complete_source_bytes, restore_complete_paths)
from complete_remaining_acceptance import validate_preservation


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def record(before, after):
    return {'beforeFileText': None if before is None else before.decode(),
        'beforeSha256': None if before is None else sha(before), 'afterSha256': sha(after)}


class CompleteRemainingSyntheticTests(unittest.TestCase):
    def test_unknown_bytes_are_visible_and_corrupt_or_stale_records_fail(self):
        self.assertEqual(pre_complete_source_bytes('knowledge/unknown.json', b'changed', records={}), b'changed')
        path = 'knowledge/hazards/H_TEST.json'
        rows = {path: record(b'old\r\n', b'new\n')}
        self.assertEqual(pre_complete_source_bytes(path, b'new\n', records=rows), b'old\r\n')
        for key in ('beforeFileText', 'beforeSha256', 'afterSha256'):
            bad = copy.deepcopy(rows); bad[path][key] = 'wrong'
            with self.subTest(key=key), self.assertRaises(AssertionError):
                pre_complete_source_bytes(path, b'new\n', records=bad)
        rows = {path: record(None, b'new')}; rows[path]['beforeSha256'] = '0' * 64
        with self.assertRaisesRegex(AssertionError, 'corrupt'):
            pre_complete_source_bytes(path, b'new', records=rows)

    def test_unknown_additions_mutations_and_removals_survive_cache(self):
        path = 'knowledge/hazards/H_TEST.json'
        rows = {path: record(b'old', b'new')}
        with tempfile.TemporaryDirectory() as tmp, patch('complete_remaining_cohort_fixture.fixture', return_value={'records': rows}):
            root = Path(tmp); p = root / path; p.parent.mkdir(parents=True); p.write_bytes(b'new')
            for name in ('docs', 'source'): (root / name).mkdir()
            unknown = root / 'knowledge/H_UNKNOWN.json'; unknown.write_bytes(b'unknown')
            first = pre_complete_repo_root(root)
            self.assertEqual((first / path).read_bytes(), b'old')
            self.assertEqual((first / unknown.relative_to(root)).read_bytes(), b'unknown')
            unknown.write_bytes(b'changed')
            second = pre_complete_repo_root(root)
            self.assertNotEqual(first, second)
            self.assertEqual((second / unknown.relative_to(root)).read_bytes(), b'changed')
            unknown.unlink(); third = pre_complete_repo_root(root)
            self.assertFalse((third / unknown.relative_to(root)).exists())
            self.assertEqual(pre_complete_repo_root(third), third)
            p.write_bytes(b'drift')
            with self.assertRaisesRegex(AssertionError, 'unexpected'): pre_complete_repo_root(root)
            p.unlink()
            with self.assertRaises(FileNotFoundError): pre_complete_repo_root(root)

    def test_only_exact_pinned_additions_can_be_removed_and_paths_are_bounded(self):
        path = 'knowledge/hazards/H_ADDED.json'
        rows = {path: record(None, b'new')}
        with tempfile.TemporaryDirectory() as tmp:
            root, target = Path(tmp) / 'current', Path(tmp) / 'prior'
            (root / path).parent.mkdir(parents=True); (root / path).write_bytes(b'new')
            shutil.copytree(root, target)
            restore_complete_paths(root, target, records=rows)
            self.assertFalse((target / path).exists())
            self.assertEqual((root / path).read_bytes(), b'new')
            for bad in ('../escape', '/tmp/escape', 'source/library/private', 'web/app.js', 'knowledge/../escape', 'knowledge//alias'):
                with self.subTest(path=bad), self.assertRaisesRegex(AssertionError, 'out-of-scope'):
                    restore_complete_paths(root, target, records={bad: record(None, b'new')})

    def test_freezer_rejects_unrecognized_changes_missing_hashes_drift_and_wrong_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
            git('init', '-q')
            p = root / 'knowledge/hazards/H_TEST.json'; p.parent.mkdir(parents=True); p.write_bytes(b'old\r\n')
            unchanged = root / 'knowledge/H_UNCHANGED.json'; unchanged.write_bytes(b'untouched')
            git('add', '.')
            git('-c', 'user.name=Fixture Test', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'baseline')
            commit, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
            (root / 'docs').mkdir()
            auth = {'baselineCommit': commit, 'baselineTree': tree, 'metadataPaths': [], 'withdrawals': {'hazards': {}, 'links': {}}}
            (root / 'docs/auth.json').write_text(json.dumps(auth))
            report_path = root / 'docs/author.json'
            report = {'baselineCommit': commit, 'baselineTree': tree,
                'authoredFiles': ['knowledge/hazards/H_TEST.json'],
                'authoredSha256': {'knowledge/hazards/H_TEST.json': sha(b'new')},
                'beforeFiles': {'knowledge/hazards/H_TEST.json': {'sha256': sha(b'old\r\n')}}}
            def save(): report_path.write_text(json.dumps(report))
            save(); p.write_bytes(b'new')
            with patch.multiple(FREEZE, BASELINE=commit, TREE=tree, REPORTS=['docs/author.json'], AUTHORIZATION='docs/auth.json'):
                frozen = FREEZE.freeze(root, commit)
                self.assertEqual(frozen['records'], {'knowledge/hazards/H_TEST.json': record(b'old\r\n', b'new')})
                # Explicit metadata overlap must keep the stronger author's pin.
                auth['metadataPaths'] = ['knowledge/hazards/H_TEST.json']
                (root / 'docs/auth.json').write_text(json.dumps(auth))
                self.assertEqual(FREEZE.freeze(root, commit)['records'], frozen['records'])
                unknown = root / 'knowledge/unknown.json'; unknown.write_text('unknown')
                with self.assertRaisesRegex(AssertionError, 'Unrecognized source changes'): FREEZE.freeze(root, commit)
                unknown.unlink(); unchanged.write_bytes(b'mutated')
                with self.assertRaisesRegex(AssertionError, 'Unrecognized source changes'): FREEZE.freeze(root, commit)
                unchanged.unlink()
                with self.assertRaisesRegex(AssertionError, 'Unrecognized source changes'): FREEZE.freeze(root, commit)
                unchanged.write_bytes(b'untouched'); p.write_bytes(b'changed after author')
                with self.assertRaisesRegex(AssertionError, 'hash drift'): FREEZE.freeze(root, commit)
                p.unlink()
                with self.assertRaisesRegex(AssertionError, 'Source removal'): FREEZE.freeze(root, commit)
                p.write_bytes(b'new'); report['authoredSha256'] = {}; save()
                with self.assertRaisesRegex(AssertionError, 'Missing or invalid'): FREEZE.freeze(root, commit)
                report['authoredSha256'] = {'knowledge/hazards/H_TEST.json': sha(b'new')}
                report['beforeFiles']['knowledge/hazards/H_TEST.json']['sha256'] = '0' * 64; save()
                with self.assertRaisesRegex(AssertionError, 'predecessor hash differs'): FREEZE.freeze(root, commit)
                with patch.object(FREEZE, 'TREE', '0' * 40), self.assertRaisesRegex(AssertionError, 'predecessor tree'):
                    FREEZE.freeze(root, commit)

    def test_author_object_paths_hash_lists_and_conflicts(self):
        path = 'knowledge/hazards/H_TEST.json'; digest = sha(b'new')
        for report in ({'authoredFiles': [{'path': path, 'sha256': digest}]},
                       {'fileHashes': [{'path': path, 'afterSha256': digest}]}):
            self.assertEqual(FREEZE.report_hashes(report), {path: digest})
        with self.assertRaisesRegex(AssertionError, 'Conflicting'):
            FREEZE.report_hashes({'authoredSha256': {path: '0' * 64}, 'authoredFiles': [{'path': path, 'sha256': digest}]})

    def test_exact_withdrawal_sets_fail_for_extra_missing_retained_and_unauthorized_details(self):
        prior = {'expectedIds': {'hazards': ['H1', 'H2'], 'links': ['K1', 'K2']}, 'changedHazardIds': ['H1', 'H2']}
        current = {'expectedIds': {'hazards': ['H1'], 'links': ['K1']}, 'changedHazardIds': ['H1'],
            'records': [{'id': 'H1', 'bases': [{'linkId': 'K1'}]}]}
        approved = {'hazards': {'H2': 'Independently reviewed source withdrawal'}, 'links': {'K2': 'Corresponding invalid source link'}}
        validate_preservation(current, prior, approved)
        for kind in ('hazards', 'links'):
            for mode in ('missing_authorization', 'extra_authorization', 'retained_withdrawal', 'other_old_missing'):
                got, authority = copy.deepcopy(current), copy.deepcopy(approved)
                if mode == 'missing_authorization': authority[kind] = {}
                elif mode == 'extra_authorization': authority[kind]['OTHER'] = 'Not in the predecessor'
                elif mode == 'retained_withdrawal': got['expectedIds'][kind].append(next(iter(approved[kind])))
                else: got['expectedIds'][kind] = []
                with self.subTest(kind=kind, mode=mode), self.assertRaises(AssertionError):
                    validate_preservation(got, prior, authority)
        for mode in ('missing_detail', 'withdrawn_detail', 'withdrawn_basis'):
            got = copy.deepcopy(current)
            if mode == 'missing_detail': got['changedHazardIds'] = []
            elif mode == 'withdrawn_detail': got['changedHazardIds'].append('H2')
            else: got['records'][0]['bases'].append({'linkId': 'K2'})
            with self.subTest(mode=mode), self.assertRaises(AssertionError): validate_preservation(got, prior, approved)


    def test_secondary_public_sets_cannot_lose_unrelated_major_or_profile_members(self):
        prior = {'expectedIds': {'hazards': ['H1', 'H2'], 'links': ['K1', 'K2'],
            'majorHazards': ['H1', 'H2'], 'profiles': ['P1', 'P2']},
            'changedHazardIds': ['H1', 'H2'], 'records': [
                {'id': 'H1', 'profiles': [{'id': 'P1'}]}, {'id': 'H2', 'profiles': [{'id': 'P2'}]}]}
        current = {'expectedIds': {'hazards': ['H1'], 'links': ['K1'], 'majorHazards': ['H1'], 'profiles': ['P1']},
            'changedHazardIds': ['H1'], 'records': [{'id': 'H1', 'bases': [{'linkId': 'K1'}]}]}
        approved = {'hazards': {'H2': 'Audited withdrawal'}, 'links': {'K2': 'Audited source withdrawal'}}
        validate_preservation(current, prior, approved)
        for kind in ('majorHazards', 'profiles'):
            got = copy.deepcopy(current); got['expectedIds'][kind] = []
            with self.subTest(kind=kind), self.assertRaisesRegex(AssertionError, 'old public membership'):
                validate_preservation(got, prior, approved)


class CompleteRemainingFrozenHistoryTests(unittest.TestCase):
    def test_all_previous_browser_and_history_fixtures_remain_exact_original_bytes(self):
        immutable = {
            'tools/browser/fixtures/residual_clauses_20261005.json': 'afd9bb3f623fc677782a22c2a72b2357d3f79b39d4ad85078581d5c81830d032',
            'tools/browser/fixtures/official_clauses_20261005.json': '69501787d0cd5405a5c3ea197d4e122e0c801520f55817d756697c7a06b949bd',
            'tools/browser/fixtures/recovery_release_20261004.json': '56f333aa5accffaca726a17f8fa3d55f9cbaff35ed4a2721a903c39ee67d381d',
            'tools/pipeline/tests/fixtures/residual_clause_cohort_20261005.json': '932bf19f529d03c23ede5fb86c46ceb296972ce9bf0ab0886d758c12e16e386d',
            'tools/pipeline/tests/fixtures/official_clause_cohort_20261005.json': 'b6e14b4651a0758844072a0a080cbc047d5724fb58366d1b79f4b3d76b296800',
            'tools/pipeline/tests/fixtures/recovery_cohort_20261004.json': 'b5cc774e369d5bf7cda5770e93c21bd76d97714bbb6d7021f2bb20c7fd37fb95',
        }
        for relative, expected in immutable.items():
            with self.subTest(path=relative): self.assertEqual(sha((ROOT / relative).read_bytes()), expected)

    def test_management_baseline_uses_the_guarded_portable_predecessor(self):
        import test_all_management_bounded_20261005 as management
        self.assertEqual(management.ROOT, ROOT)
        self.assertEqual(management.BASE, pre_complete_repo_root(ROOT))

    def test_final_inverse_matches_report_pins_and_exact_git_predecessor(self):
        data = fixture()
        self.assertEqual(data['baselineCommit'], FREEZE.BASELINE)
        self.assertEqual(data['baselineTree'], FREEZE.TREE)
        allowed, _ = FREEZE.authorized_hashes(ROOT)
        self.assertLessEqual(set(data['records']), set(allowed))
        self.assertTrue(data['records'])
        for path, row in data['records'].items():
            raw = (ROOT / path).read_bytes()
            self.assertEqual(sha(raw), row['afterSha256'], path)
            self.assertEqual(pre_complete_source_bytes(path, raw), None if row['beforeFileText'] is None else row['beforeFileText'].encode())
        for path, digest in data['authoredReportSha256'].items():
            self.assertEqual(sha((ROOT / path).read_bytes()), digest)
        self.assertEqual(sha((ROOT / data['authorizationPath']).read_bytes()), data['authorizationSha256'])

    def test_historical_chain_restores_each_immutable_browser_source_snapshot(self):
        from residual_clause_cohort_fixture import pre_residual_repo_root
        from official_clause_cohort_fixture import pre_official_repo_root
        from release_snapshot import source_hashes, snapshot_digest
        for materialize, filename in ((pre_complete_repo_root, 'residual_clauses_20261005.json'),
                                     (pre_residual_repo_root, 'official_clauses_20261005.json'),
                                     (pre_official_repo_root, 'recovery_release_20261004.json')):
            original = json.loads((ROOT / 'tools/browser/fixtures' / filename).read_text())
            self.assertEqual(snapshot_digest(source_hashes(materialize(ROOT) / 'knowledge')), original['knowledgeSnapshotHash'])


if __name__ == '__main__':
    unittest.main()
