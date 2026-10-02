"""Official replacement metadata fixes an exclusive end date, not admission."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
import release_gate_core as gate

OLD = 'LV_STD_GBT13869_2017'
NEW = 'LV_STD_GBT13869_2026'


class Gbt13869DateBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.version = json.loads((KNOW / 'law-versions' / (OLD + '.json')).read_text())
        cls.review = json.loads((KNOW / 'reviews/law-versions' / (OLD + '.json')).read_text())
        cls.results = {day: gate.evaluate_release_gate(KNOW, date.fromisoformat(day))
                       for day in ('2027-01-30', '2027-01-31', '2027-02-01')}
        clauses = {cid for cid, row in gate.load_dir(KNOW, 'clauses').items()
                   if row['lawVersionId'] == OLD}
        cls.old_links = {kid for kid, row in gate.load_dir(KNOW, 'links').items()
                         if row['clauseId'] in clauses}

    def test_old_version_and_all_ten_current_links_survive_january_31(self):
        before, last = self.results['2027-01-30'], self.results['2027-01-31']
        for result in (before, last):
            self.assertTrue(result.law_versions[OLD]['ok'])
            self.assertTrue(result.law_versions[OLD]['supports_current'])
            # Preserve PR103's exact ten pre-existing links; separately pin the newly reviewed cord atom.
            atom = 'K_COM_PLUGSTRIP_CORD_GBT13869_5_2_2'
            self.assertIn(atom, self.old_links)
            self.assertIn(atom, result.eligible_links)
            self.assertEqual(len(result.eligible_links & (self.old_links - {atom})), 10)
            self.assertEqual(len(result.eligible_links & self.old_links), 11)
        self.assertEqual(before.eligible_links, last.eligible_links)
        self.assertEqual(before.eligible_hazards, last.eligible_hazards)

    def test_old_version_expires_on_february_1_and_no_successor_is_activated(self):
        after = self.results['2027-02-01']
        self.assertFalse(after.law_versions[OLD]['supports_current'])
        self.assertIn('BLOCK_VERSION_EXPIRED:active_past_endDate',
                      after.law_versions[OLD]['reasons'])
        self.assertFalse(after.eligible_links & self.old_links)
        for result in self.results.values():
            self.assertEqual(result.law_versions[NEW]['validityStatus'], 'upcoming')
            self.assertFalse(result.law_versions[NEW]['supports_current'])
        self.assertIn('BLOCK_VERSION_NOT_EFFECTIVE:upcoming_not_future',
                      after.law_versions[NEW]['reasons'])

    def test_original_inclusive_last_day_as_endpoint_reproduces_the_gap(self):
        original = copy.deepcopy(self.version)
        original['endDate'] = '2027-01-31'
        review = self.review['previousReview']
        self.assertEqual(content_hash(original), review['reviewedContentHash'])
        _, supports, reasons = gate.gate_law_version(
            original, review, True, date(2027, 1, 31))
        self.assertFalse(supports)
        self.assertIn('BLOCK_VERSION_EXPIRED:active_past_endDate', reasons)

    def test_metadata_change_requires_its_own_current_review_binding(self):
        ok, _, reasons = gate.gate_law_version(
            self.version, self.review['previousReview'], True, date(2027, 1, 31))
        self.assertFalse(ok)
        self.assertIn('BLOCK_REVIEW_STALE', reasons)
        self.assertEqual(self.review['reviewedContentHash'], content_hash(self.version))
        self.assertEqual(self.version['endDate'], self.version['supersededEffectiveDate'])

    def test_prior_review_and_successor_bytes_are_preserved(self):
        prior_bytes = (json.dumps(self.review['previousReview'], ensure_ascii=False,
                                 indent=2) + '\n').encode()
        self.assertEqual(hashlib.sha256(prior_bytes).hexdigest(),
                         self.review['previousReviewFileSha256'])
        self.assertEqual(self.review['previousReviewFileSha256'],
                         '45347f2893b73acd42faab4beffff3b647e59c0fab0dbc964071113381050c4e')
        self.assertEqual(hashlib.sha256((KNOW / 'law-versions' / (NEW + '.json'))
                                       .read_bytes()).hexdigest(),
                         '3a32dcbad827d26a7935ea2dc48fe738381d4b75f0d7dae8c34a3eff360bc4cb')


if __name__ == '__main__':
    unittest.main()
