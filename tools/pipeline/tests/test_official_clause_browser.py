"""Current official-clause browser pins, preserving all earlier recovery coverage."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
from residual_clause_cohort_fixture import pre_residual_repo_root
ROOT = pre_residual_repo_root(ROOT)
sys.path[:0] = [str(ROOT / 'tools/browser'), str(ROOT / 'tools/v4')]
import official_clause_acceptance as CURRENT
import recovery_release_acceptance as QA
from freeze_recovery_expectations import project_expectations
from release_gate_core import evaluate_release_gate, load_dir
from release_snapshot import source_hashes, snapshot_digest

FORMAL = {
    'H_4E5F4BB13B82457DA5377CABDF',
    'H_GB51309_SELF_POWERED_PLUG', 'H_GB12801_ACCIDENT_EXHAUST_INTERLOCK',
    'H_200F007CE0EF47DFB8BE2B8618', 'H_GBT34525_PREUSE_CHECK',
    'H_GB55037_BUILDING_GAS_ALARM', 'H_GB3836_UNUSED_ENTRY',
    'H_GB3836_EX_D_MISSING_FASTENER',
}
PENDING = {
    'H_GBT14561_HOSE_PLACEMENT',
    'H_8C14C2BD0D4A4EF1B42FDC8C2E', 'H_BF7AA7549F8E1B94012882C9',
    'H_C1CE3A649721387F1FC0F7BE', 'H_1B474A2ABA0E23143E2FE451',
}


def projection(fixture):
    value = copy.deepcopy(fixture['expectedIds'])
    value['lawClauses'] = value['clauses'][:]
    value['details'] = [
        {'id': row['id'], 'hazard': {**copy.deepcopy(row['hazard']), 'displayCategory': row['displayCategory']},
         'bases': copy.deepcopy(row['bases'])} for row in fixture['records']]
    return value


class OfficialClauseBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = CURRENT.load_expectations()
        cls.legacy = QA.load_expectations()

    def test_current_snapshot_whole_membership_eight_details_and_candidate_exclusion(self):
        f = self.current
        self.assertEqual(f['asOf'], '2026-10-05')
        QA.validate_source_pins(f, ROOT)
        gate = evaluate_release_gate(ROOT / 'knowledge', date.fromisoformat(f['asOf']))
        links = load_dir(ROOT / 'knowledge', 'links')
        kids = {kid for kid in gate.eligible_links if links[kid]['hazardId'] in gate.eligible_hazards}
        self.assertEqual(f['expectedIds']['hazards'], sorted(gate.eligible_hazards))
        self.assertEqual(f['expectedIds']['links'], sorted(kids))
        self.assertEqual(f['expectedIds']['clauses'], sorted({links[kid]['clauseId'] for kid in kids}))
        self.assertLessEqual(FORMAL, set(f['changedHazardIds']))
        self.assertLessEqual(set(self.legacy['changedHazardIds']), set(f['changedHazardIds']))
        self.assertFalse(PENDING & set(f['expectedIds']['hazards']))
        self.assertFalse(PENDING & set(f['changedHazardIds']))
        excluded_links = {'K_XLSX_WEB_' + hid for hid in PENDING if hid != 'H_GBT14561_HOSE_PLACEMENT'}
        excluded_links.update({'K_GBT14561_HOSE_5_6_1', 'K_GBT14561_HOSE_5_6_2'})
        self.assertFalse(excluded_links & set(f['expectedIds']['links']))

    def test_current_freeze_is_reproducible_only_from_source_and_saved_change_hashes(self):
        f = self.current
        hashes = source_hashes(ROOT / 'knowledge')
        baseline = dict(hashes)
        for path, change in f['sourceChanges'].items():
            self.assertEqual(hashes.get(path), change['afterSha256'])
            if change['beforeSha256'] is None:
                baseline.pop(path, None)
            else:
                baseline[path] = change['beforeSha256']
        reproduced = project_expectations(ROOT / 'knowledge', date.fromisoformat(f['asOf']),
            hashes=hashes, baseline_commit=f['baselineCommit'], baseline=baseline)
        reproduced['knowledgeSnapshotHash'] = snapshot_digest(hashes)
        self.assertEqual(reproduced, f)

    def test_old_freeze_stays_immutable_and_cannot_authorize_current_source(self):
        old_bytes = QA.FIXTURE.read_bytes()
        self.assertEqual(self.legacy['asOf'], '2026-10-04')
        self.assertNotEqual(CURRENT.FIXTURE, QA.FIXTURE)
        with self.assertRaisesRegex(AssertionError, 'source snapshot changed'):
            QA.validate_source_pins(self.legacy, ROOT)
        self.assertEqual(QA.FIXTURE.read_bytes(), old_bytes)
        with self.assertRaisesRegex(AssertionError, 'not the source-pinned'):
            QA.validate_release_source(self.current, {'releaseHash': 'a' * 64, 'asOf': self.current['asOf'],
                'knowledge': {'snapshotSha256': self.legacy['knowledgeSnapshotHash']}}, 'a' * 64)

    def test_every_new_business_field_and_exact_basis_is_checked_by_shared_browser_contract(self):
        QA.validate_projection(self.current, projection(self.current))
        for hid in FORMAL:
            original = next(row for row in self.current['records'] if row['id'] == hid)
            for field in ('title', 'description', 'conditions', 'measures', 'category', 'places'):
                got = projection(self.current)
                row = next(row for row in got['details'] if row['id'] == hid)
                row['hazard'][field] = ['wrong'] if field == 'places' else 'wrong'
                with self.subTest(hazard=hid, field=field), self.assertRaises(AssertionError):
                    QA.validate_projection(self.current, got)
            for index, basis in enumerate(original['bases']):
                for field in ('linkId', 'clauseId', 'article', 'quote', 'role', 'applicability', 'sourceUrl', 'lawRegion'):
                    got = projection(self.current)
                    row = next(row for row in got['details'] if row['id'] == hid)
                    row['bases'][index][field] = 'wrong'
                    with self.subTest(hazard=hid, basis=index, field=field), self.assertRaises(AssertionError):
                        QA.validate_projection(self.current, got)

    def test_new_copy_keeps_all_direct_and_supporting_sources_and_boundaries(self):
        for row in self.current['records']:
            if row['id'] not in FORMAL:
                continue
            plain = QA.expected_clipboard(row)
            full = QA.expected_full_clipboard(row, 'test.official')
            self.assertTrue(full.startswith(plain + '\n\n'))
            self.assertTrue(full.endswith('数据库版本：test.official。'))
            for basis in row['bases']:
                self.assertIn(basis['quote'], plain)
                self.assertIn(basis['applicability'], plain)

    def test_current_date_advance_requires_exact_full_source_projection(self):
        projected = QA.fixture_for_release_date(self.current, '2026-10-06', ROOT)
        expected = copy.deepcopy(self.current); expected['asOf'] = '2026-10-06'
        self.assertEqual(projected, expected)
        with self.assertRaisesRegex(AssertionError, 'new review and freeze'):
            QA.fixture_for_release_date(self.current, '2027-02-01', ROOT)

    def test_production_harness_selects_new_fixture_and_keeps_all_existing_rendered_flows(self):
        for name in ('audit_browser.py', 'audit_ordinary_tables.py'):
            text = (ROOT / 'tools/browser' / name).read_text()
            self.assertIn('from residual_clause_acceptance import load_expectations', text)
        shared = (ROOT / 'tools/browser/recovery_release_acceptance.py').read_text()
        for token in ('for width in (1440, 375, 390, 485)', 'for row in rows:', 'page.go_back()',
                      'page.go_forward()', 'page.reload(', 'navigator.clipboard.readText()',
                      'recovery_exact_public_membership_after_flows'):
            self.assertIn(token, shared)


if __name__ == '__main__':
    unittest.main()
