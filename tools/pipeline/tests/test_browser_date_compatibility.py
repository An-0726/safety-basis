"""Date advancement is an equal-source projection proof, never an approval."""
import ast
import copy
from datetime import date
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools/browser'), str(ROOT / 'tools/v4')]
import recovery_release_acceptance as QA
import audit_browser as AUDIT
F = QA.load_expectations()


class BrowserDateCompatibilityTests(unittest.TestCase):
    def test_next_day_equal_source_projection_is_in_memory_only(self):
        raw = QA.FIXTURE.read_bytes()
        current = QA.fixture_for_release_date(F, '2026-10-05', ROOT)
        wanted = copy.deepcopy(F); wanted['asOf'] = '2026-10-05'
        self.assertEqual(current, wanted)
        self.assertEqual(QA.FIXTURE.read_bytes(), raw)
        self.assertEqual(F['asOf'], '2026-10-04')

    def test_reverse_malformed_and_noncanonical_dates_fail(self):
        for day in ('2026-10-03', 'not-a-date', None, '20261005', '2026-10-5'):
            with self.subTest(day=day), self.assertRaises(AssertionError):
                QA.fixture_for_release_date(F, day, ROOT)

    def test_actual_exclusive_version_boundaries_require_a_new_review(self):
        for day in ('2026-11-01', '2027-02-01'):
            with self.subTest(day=day), self.assertRaisesRegex(AssertionError, 'new review and freeze'):
                QA.fixture_for_release_date(F, day, ROOT)

    def test_same_ids_but_changed_full_profile_or_major_body_fail(self):
        for changed in ('profiles', 'majorCatalog', 'majorTopic', 'references', 'directory', 'reading'):
            before = {key: {'records': ['unchanged']} for key in ('profiles', 'majorCatalog', 'majorTopic', 'references', 'directory', 'reading')}
            after = copy.deepcopy(before); after[changed]['records'] = ['different exact content with same id']
            with self.subTest(projection=changed), patch.object(QA, 'full_dated_public_projections', side_effect=[before, after]), self.assertRaisesRegex(AssertionError, 'complete public projection'):
                QA.fixture_for_release_date(F, '2026-10-05', ROOT)

    def test_source_drift_blocks_same_and_later_dates(self):
        for day in ('2026-10-04', '2026-10-05'):
            with patch.object(QA, 'validate_source_pins', side_effect=AssertionError('source drift')), self.assertRaisesRegex(AssertionError, 'source drift'):
                QA.fixture_for_release_date(F, day, ROOT)

    def test_invalid_identity_keeps_observation_and_never_creates_verified_release(self):
        release = {'releaseHash': 'a' * 64, 'asOf': F['asOf'], 'counts': {'hazards': 1}, 'knowledge': {'snapshotSha256': 'wrong'}}
        manifest = {'releaseHash': 'a' * 64, 'counts': {'hazards': 1}, 'dataVersion': '2026.10.04.test'}
        report = {'observeOnly': True, 'checks': []}
        with patch.object(AUDIT, 'fixture_for_release_date', return_value=F), self.assertRaisesRegex(AssertionError, 'source-pinned'):
            AUDIT.bind_observed_release(report, F, release, manifest, ROOT)
        self.assertEqual(report['observedRelease']['releaseHash'], 'a' * 64)
        self.assertNotIn('release', report)
        with self.assertRaisesRegex(AssertionError, 'blocked'):
            AUDIT.require_verified_release(report)
        # The failure is recordable under --observe and remains failed in strict mode.
        report['checks'].append({'name': 'identity', 'pass': False})
        self.assertEqual(sum(not c['pass'] for c in report['checks']), 1)

    def test_valid_identity_then_mixed_release_fails(self):
        release = {'releaseHash': 'a' * 64, 'asOf': F['asOf'], 'counts': {'hazards': 1}, 'knowledge': {'snapshotSha256': F['knowledgeSnapshotHash']}}
        manifest = {'releaseHash': 'a' * 64, 'counts': {'hazards': 1}, 'dataVersion': '2026.10.04.test'}
        report = {}
        with patch.object(AUDIT, 'fixture_for_release_date', return_value=F):
            AUDIT.bind_observed_release(report, F, release, manifest, ROOT)
            self.assertEqual(AUDIT.require_verified_release(report)['releaseHash'], 'a' * 64)
            release['releaseHash'] = manifest['releaseHash'] = 'b' * 64
            with self.assertRaisesRegex(AssertionError, 'changed during'):
                AUDIT.bind_observed_release(report, F, release, manifest, ROOT)
        self.assertEqual(report['release']['releaseHash'], 'a' * 64)

    def test_all_source_pinned_browser_flows_are_guarded_on_verified_identity(self):
        tree = ast.parse((ROOT / 'tools/browser/audit_browser.py').read_text())
        guarded = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
            and ast.unparse(n.test) == "report.get('release')"
            and any('run_repair_browser_acceptance' in ast.unparse(x) for x in n.body))
        for name in ('run_repair_browser_acceptance', 'run_technical_browser_acceptance', 'run_electrical_browser_acceptance', 'run_recovery_release_acceptance'):
            self.assertIn(name, ast.unparse(guarded))
        self.assertIn('require_verified_release', ast.unparse(guarded.orelse[0]))
        self.assertIn('fixture_for_release_date', (ROOT / 'tools/browser/audit_ordinary_tables.py').read_text())


if __name__ == '__main__':
    unittest.main()
