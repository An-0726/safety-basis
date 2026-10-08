"""Temporal scanner findings must use the requested snapshot and retain severity."""
from datetime import date
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
V4 = ROOT / 'tools/v4'
sys.path.insert(0, str(V4))
import comprehensive_scanner as scanner
from canonical import content_hash


class ExplicitScanDateTests(unittest.TestCase):
    def rows(self):
        hazard = {'id': 'H_TEST', 'title': 'Test defective equipment', 'lifecycle': 'active'}
        clause = {'id': 'C_TEST', 'lawVersionId': 'LV_TEST', 'quote': 'Complete test rule'}
        link = {'id': 'K_TEST', 'hazardId': 'H_TEST', 'clauseId': 'C_TEST', 'lifecycle': 'active'}
        review = lambda row: {'decision': 'verified', 'reviewedContentHash': content_hash(row)}
        return {
            'hazards': {'H_TEST': hazard}, 'clauses': {'C_TEST': clause},
            'links': {'K_TEST': link}, 'laws': {},
            'law-versions': {'LV_TEST': {'id': 'LV_TEST', 'validityStatus': 'active',
                                        'effectiveDate': '2026-10-01', 'endDate': '2026-11-01'}},
            'reviews/hazards': {'H_TEST': review(hazard)},
            'reviews/clauses': {'C_TEST': review(clause)},
            'reviews/links': {'K_TEST': review(link)},
        }

    def scan(self, at, rows=None):
        with patch.object(scanner, 'load_dir', side_effect=(rows or self.rows()).__getitem__):
            return scanner.run_scan(at)

    def test_effective_day_and_exclusive_end(self):
        before = self.scan(date(2026, 9, 30))
        self.assertEqual([r['rule_id'] for r in before], ['RULE_UPCOMING_VERSION_ACTIVE_LINK'])
        self.assertEqual(before[0]['severity'], 'ERROR')
        self.assertEqual(before[0]['asOf'], '2026-09-30')
        self.assertEqual(self.scan(date(2026, 10, 1)), [])
        self.assertEqual(self.scan(date(2026, 10, 31)), [])
        expired = self.scan(date(2026, 11, 1))
        self.assertEqual([r['rule_id'] for r in expired], ['RULE_REPEALED_VERSION_ACTIVE_LINK'])
        self.assertEqual(expired[0]['severity'], 'ERROR')
        self.assertEqual(expired[0]['asOf'], '2026-11-01')

    def test_upcoming_status_is_not_automatically_promoted(self):
        rows = self.rows()
        rows['law-versions']['LV_TEST']['validityStatus'] = 'upcoming'
        findings = self.scan(date(2026, 10, 1), rows)
        self.assertEqual(findings[0]['rule_id'], 'RULE_UPCOMING_VERSION_ACTIVE_LINK')
        self.assertEqual(findings[0]['severity'], 'ERROR')

    def test_date_is_mandatory_and_validated(self):
        with self.assertRaises(TypeError):
            scanner.run_scan()
        with self.assertRaises(TypeError):
            scanner.run_scan('2026-10-04')
        for args in ([], ['--as-of', '2026-02-30']):
            run = subprocess.run([sys.executable, str(V4 / 'comprehensive_scanner.py'), *args],
                                 capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)

    def test_ci_builds_with_an_explicit_china_date(self):
        workflow = (ROOT / '.github/workflows/site.yml').read_text(encoding='utf-8')
        self.assertIn('BUILD_DATE="$(TZ=Asia/Shanghai date +%F)"', workflow)
        build_line = next(line for line in workflow.splitlines() if 'build_unified_release.py' in line)
        self.assertIn('--as-of "${BUILD_DATE}"', build_line)

if __name__ == '__main__':
    unittest.main()
