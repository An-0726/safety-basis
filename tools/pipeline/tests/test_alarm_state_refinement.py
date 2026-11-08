"""The alarm state split must retain the precise current basis and old rejection."""
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from release_gate_core import evaluate_release_gate


class AlarmStateRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = evaluate_release_gate(str(ROOT / 'knowledge'), date(2026, 11, 8))

    def read(self, path):
        return json.loads((ROOT / 'knowledge' / path).read_text(encoding='utf-8'))

    def test_old_misaligned_design_clause_stays_out_of_public_basis(self):
        old = 'K_XLSX_WEB_H_0A53849CB39848628056FDADEB'
        self.assertNotIn(old, self.gate.eligible_links)
        review = self.read('reviews/links/' + old + '.json')
        self.assertEqual(review['decision'], 'rejected')
        self.assertEqual(review['previousReview']['decision'], 'rejected')

    def test_admitted_candidate_uses_current_complete_article_and_bounded_scope(self):
        hid = 'H_0A53849CB39848628056FDADEB'
        kid = 'K_HAZCHEM_ALARM_SERVICEABILITY_20261108'
        self.assertIn(hid, self.gate.eligible_hazards)
        self.assertIn(kid, self.gate.eligible_links)
        link = self.read('links/' + kid + '.json')
        clause = self.read('clauses/' + link['clauseId'] + '.json')
        self.assertEqual(clause['lawVersionId'], 'LV_HAZCHEM_LAW')
        self.assertEqual(clause['articlePath'], '第三十八条')
        self.assertIn('并保证处于适用状态', clause['quote'])
        self.assertIn('不得篡改、隐瞒、销毁', clause['quote'])
        self.assertIn('必须确认装置已经设置及实际功能异常', link['applicability'])
        self.assertIn('资料未提供', link['applicability'])

    def test_absent_and_failed_states_keep_separate_ids_and_history(self):
        absent = self.read('hazards/H_2456A494C71E6807975B908C_1.json')
        failed = self.read('hazards/H_0A53849CB39848628056FDADEB.json')
        self.assertNotEqual(absent['id'], failed['id'])
        self.assertIn('未设置', absent['title'])
        self.assertIn('已设置', failed['title'])
        self.assertNotIn('或者', absent['title'])
        for row in (absent, failed):
            review = self.read('reviews/hazards/' + row['id'] + '.json')
            self.assertEqual(review['previousEntity']['id'], row['id'])
            self.assertFalse(review['reviewEvidence']['siteFactsVerified'])

    def test_original_communication_failure_obligation_is_not_lost(self):
        hid = 'H_HAZCHEM_COMMUNICATION_DEVICE_INOPERABLE'
        kid = 'K_HAZCHEM_COMMUNICATION_SERVICEABILITY_20261108'
        self.assertIn(hid, self.gate.eligible_hazards)
        self.assertIn(kid, self.gate.eligible_links)
        hazard = self.read('hazards/' + hid + '.json')
        self.assertIn('通信装置未保持适用状态', hazard['title'])
        self.assertIn('资料未提供', hazard['conditions'])
        link = self.read('links/' + kid + '.json')
        self.assertEqual(link['clauseId'], 'C_2456A494C71E6807975B908C')
        original = self.read('hazards/H_2456A494C71E6807975B908C_1.json')
        self.assertIn(hid, original['conditions'])


if __name__ == '__main__':
    unittest.main()
