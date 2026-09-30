"""Exclusive version end dates must not expire a standard one day early."""
import copy
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4'))
from canonical import content_hash
from release_gate_core import gate_law_version, gate_clause, evaluate_release_gate


class VersionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.version = {'id': 'SYN_V', 'lawId': 'SYN_L', 'versionKey': 'test',
                        'effectiveDate': '2020-01-01', 'endDate': '2026-10-01',
                        'validityStatus': 'active'}
        self.review = {'decision': 'verified', 'evidenceRefs': ['SYN_E'],
                       'reviewedContentHash': content_hash(self.version)}
        self.clause = {'id': 'SYN_C', 'lawVersionId': 'SYN_V',
                       'articlePath': 'synthetic', 'quote': 'Synthetic test text'}
        self.clause_review = {'decision': 'verified', 'evidenceRefs': ['SYN_E'],
                              'reviewedContentHash': content_hash(self.clause)}

    def test_day_before_exclusive_end_is_current(self):
        ok, current, reasons = gate_law_version(self.version, self.review, True, date(2026, 9, 30))
        self.assertTrue(ok and current)
        self.assertEqual(reasons, [])

    def test_exact_end_excludes_without_losing_temporal_reason(self):
        ok, current, reasons = gate_law_version(self.version, self.review, True, date(2026, 10, 1))
        self.assertFalse(ok or current)
        clause_ok, clause_reasons = gate_clause(self.clause, self.clause_review, current, ok,
                                                self.version, reasons)
        self.assertFalse(clause_ok)
        self.assertIn('BLOCK_VERSION_EXPIRED:active_past_endDate', clause_reasons)
        self.assertNotIn('BLOCK_VERSION_UNKNOWN:lawVersion_gate_failed', clause_reasons)

    def test_expiry_must_not_hide_stale_version_review(self):
        review = copy.deepcopy(self.review)
        review['reviewedContentHash'] = 'stale'
        ok, current, reasons = gate_law_version(self.version, review, True, date(2026, 10, 1))
        _, clause_reasons = gate_clause(self.clause, self.clause_review, current, ok,
                                        self.version, reasons)
        self.assertIn('BLOCK_VERSION_UNKNOWN:lawVersion_gate_failed', clause_reasons)
        self.assertNotIn('BLOCK_VERSION_EXPIRED:active_past_endDate', clause_reasons)

    def test_governed_old_standard_expires_on_successor_effective_day(self):
        root = Path(__file__).resolve().parents[3] / 'knowledge'
        before = evaluate_release_gate(root, date(2026, 9, 30))
        after = evaluate_release_gate(root, date(2026, 10, 1))
        version_id = 'LV_STD_GB12801_2008'
        self.assertTrue(before.law_versions[version_id]['supports_current'])
        self.assertFalse(after.law_versions[version_id]['supports_current'])
        link_id = 'K_XLSX_WEB_H_CE94D2ACC8C544BCA0FB0AA026'
        self.assertIn(link_id, before.eligible_links)
        self.assertNotIn(link_id, after.eligible_links)


if __name__ == '__main__':
    unittest.main()
