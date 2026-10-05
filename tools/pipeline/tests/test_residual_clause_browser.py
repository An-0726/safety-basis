"""Current residual browser source, every inherited detail and drift negatives."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
from complete_remaining_cohort_fixture import pre_complete_repo_root
ROOT = pre_complete_repo_root(ROOT)
sys.path[:0] = [str(ROOT / 'tools/browser'), str(ROOT / 'tools/v4')]
import residual_clause_acceptance as CURRENT
import official_clause_acceptance as OFFICIAL
import recovery_release_acceptance as QA
from freeze_recovery_expectations import project_expectations
from freeze_residual_clause_history import REPORT_FIELDS
from residual_clause_cohort_fixture import fixture as history_fixture, pre_residual_repo_root
from release_gate_core import evaluate_release_gate, load_dir
from release_snapshot import source_hashes, snapshot_digest

FORMAL = {
    'H053', 'H054', 'H055', 'H_993643C76F7041BDA19B0C5EED',
    'H_D128C0FCC4844BD8BF5D8FAAF5', 'H_8A733CAD776643E3B34B4D4689',
    'H_B0B7C75B5F0D423386A84AB73D',
    'H_CFF821DDE6764083BFB914EC86', 'H_3141FAD634694686B722139F91',
    'H_C7284453E8E94532A44FC5F5EF', 'H_974023DBBC2B471AA3F7DB6A67',
}


def projection(fixture):
    result = copy.deepcopy(fixture['expectedIds'])
    result['lawClauses'] = result['clauses'][:]
    result['details'] = [
        {'id': row['id'], 'hazard': {**copy.deepcopy(row['hazard']), 'displayCategory': row['displayCategory']},
         'bases': copy.deepcopy(row['bases'])} for row in fixture['records']]
    return result


class ResidualClauseBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = CURRENT.load_expectations()
        cls.official = OFFICIAL.load_expectations()
        cls.authored_ids = set()
        for relative in REPORT_FIELDS:
            report = json.loads((ROOT / relative).read_text())
            cls.authored_ids.update(r['hazardId'] for r in report.get('decisions', []) if 'hazardId' in r)
        cls.public_authored = cls.authored_ids & set(cls.current['expectedIds']['hazards'])

    def test_current_whole_membership_is_source_derived_with_every_formal_and_inherited_detail(self):
        f = self.current
        self.assertEqual(f['asOf'], '2026-10-05')
        QA.validate_source_pins(f, ROOT)
        gate = evaluate_release_gate(ROOT / 'knowledge', date.fromisoformat(f['asOf']))
        links = load_dir(ROOT / 'knowledge', 'links')
        kids = {kid for kid in gate.eligible_links if links[kid]['hazardId'] in gate.eligible_hazards}
        self.assertEqual(f['expectedIds']['hazards'], sorted(gate.eligible_hazards))
        self.assertEqual(f['expectedIds']['links'], sorted(kids))
        self.assertEqual(f['expectedIds']['clauses'], sorted({links[kid]['clauseId'] for kid in kids}))
        self.assertEqual(len(self.official['records']), 199)
        self.assertLessEqual(set(self.official['changedHazardIds']), set(f['changedHazardIds']))
        self.assertLessEqual(FORMAL, self.public_authored)
        self.assertLessEqual(self.public_authored, set(f['changedHazardIds']))
        self.assertFalse((self.authored_ids - gate.eligible_hazards) & set(f['changedHazardIds']))

    def test_current_freeze_reproduces_from_exact_source_and_covers_every_batch_source_change(self):
        f = self.current
        hashes = source_hashes(ROOT / 'knowledge')
        baseline = dict(hashes)
        for path, change in f['sourceChanges'].items():
            self.assertEqual(hashes.get(path), change['afterSha256'])
            if change['beforeSha256'] is None: baseline.pop(path, None)
            else: baseline[path] = change['beforeSha256']
        reproduced = project_expectations(ROOT / 'knowledge', date.fromisoformat(f['asOf']),
            hashes=hashes, baseline_commit=f['baselineCommit'], baseline=baseline)
        reproduced['knowledgeSnapshotHash'] = snapshot_digest(hashes)
        self.assertEqual(reproduced, f)
        for relative, row in history_fixture()['records'].items():
            if not relative.startswith('knowledge/'): continue
            path = relative.removeprefix('knowledge/')
            self.assertIn(path, f['sourceChanges'])
            self.assertEqual(f['sourceChanges'][path]['afterSha256'], row['afterSha256'])
        for row in f['records']:
            self.assertLessEqual(set(row['changedDependencies']), set(f['sourceChanges']))

    def test_previous_freeze_is_historical_only_and_cannot_authorize_current_source(self):
        self.assertNotEqual(CURRENT.FIXTURE, OFFICIAL.FIXTURE)
        self.assertNotEqual(self.current['knowledgeSnapshotHash'], self.official['knowledgeSnapshotHash'])
        QA.validate_source_pins(self.official, pre_residual_repo_root(ROOT))
        with self.assertRaisesRegex(AssertionError, 'source snapshot changed'):
            QA.validate_source_pins(self.official, ROOT)
        for old in (self.official, QA.load_expectations()):
            with self.assertRaisesRegex(AssertionError, 'not the source-pinned'):
                QA.validate_release_source(self.current, {'releaseHash': 'a' * 64, 'asOf': self.current['asOf'],
                    'knowledge': {'snapshotSha256': old['knowledgeSnapshotHash']}}, 'a' * 64)

    def test_each_formal_business_field_and_every_basis_rejects_mutation(self):
        QA.validate_projection(self.current, projection(self.current))
        self.assertTrue(self.public_authored)
        for hid in self.public_authored:
            original = next(row for row in self.current['records'] if row['id'] == hid)
            for field in ('title', 'description', 'conditions', 'measures', 'category', 'places', 'checked', 'status'):
                got = projection(self.current)
                row = next(row for row in got['details'] if row['id'] == hid)
                row['hazard'][field] = ['wrong'] if field == 'places' else 'wrong'
                with self.subTest(hazard=hid, field=field), self.assertRaises(AssertionError):
                    QA.validate_projection(self.current, got)
            for index, basis in enumerate(original['bases']):
                for field in ('linkId', 'clauseId', 'lawId', 'lawName', 'article', 'quote', 'role', 'applicability', 'sourceUrl', 'jurisdictionCode', 'clauseRegion', 'lawRegion'):
                    got = projection(self.current)
                    row = next(row for row in got['details'] if row['id'] == hid)
                    row['bases'][index][field] = 'wrong'
                    with self.subTest(hazard=hid, basis=index, field=field), self.assertRaises(AssertionError):
                        QA.validate_projection(self.current, got)

    def test_current_exact_membership_detects_same_count_swaps_duplicates_and_missing_items(self):
        for key in (*QA.PUBLIC_SETS, 'lawClauses'):
            for mode in ('swap', 'duplicate', 'missing'):
                got = projection(self.current)
                if mode == 'swap': got[key][-1] += '_UNEXPECTED'
                elif mode == 'duplicate': got[key][-1] = got[key][0]
                else: got[key].pop()
                with self.subTest(key=key, mode=mode), self.assertRaises(AssertionError):
                    QA.validate_projection(self.current, got)

    def test_full_source_pins_reject_unlisted_additions_removals_and_known_byte_drift(self):
        hashes = source_hashes(ROOT / 'knowledge')
        for mode in ('unknown_addition', 'removal', 'known_mutation'):
            changed = dict(hashes)
            if mode == 'unknown_addition': changed['hazards/H_UNREVIEWED.json'] = '0' * 64
            elif mode == 'removal': del changed[next(iter(changed))]
            else: changed['hazards/H053.json'] = '0' * 64
            with self.subTest(mode=mode), patch('release_snapshot.source_hashes', return_value=changed):
                with self.assertRaisesRegex(AssertionError, 'source snapshot changed'):
                    QA.validate_source_pins(self.current, ROOT)

    def test_copy_preserves_all_current_quotes_applicability_and_source_notes(self):
        for row in self.current['records']:
            if row['id'] not in self.public_authored: continue
            plain = QA.expected_clipboard(row)
            full = QA.expected_full_clipboard(row, 'test.residual')
            self.assertTrue(full.startswith(plain + '\n\n'))
            self.assertTrue(full.endswith('数据库版本：test.residual。'))
            for basis in row['bases']:
                self.assertIn(basis['quote'], plain)
                self.assertIn(basis['applicability'], plain)

    def test_date_advance_requires_identical_complete_projection(self):
        projected = QA.fixture_for_release_date(self.current, '2026-10-06', ROOT)
        expected = copy.deepcopy(self.current); expected['asOf'] = '2026-10-06'
        self.assertEqual(projected, expected)
        with self.assertRaisesRegex(AssertionError, 'new review and freeze'):
            QA.fixture_for_release_date(self.current, '2027-02-01', ROOT)

    def test_historical_loader_keeps_its_original_fixture_and_render_contract(self):
        # Production-entry identity assertions move intact to the newer complete
        # batch test. This cohort still requires its original residual bytes and
        # exact source projection through the explicit inverse above.
        self.assertEqual(CURRENT.load_expectations(), self.current)
        shared = (ROOT / 'tools/browser/recovery_release_acceptance.py').read_text()
        for token in ('for width in (1440, 375, 390, 485)', 'for row in rows:', 'page.go_back()',
                      'page.go_forward()', 'page.reload(', 'navigator.clipboard.readText()',
                      'recovery_exact_public_membership_after_flows'):
            self.assertIn(token, shared)


if __name__ == '__main__':
    unittest.main()
