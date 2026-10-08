"""Pending-source batch 1: exact bounded rules, kept candidates and the corrected GB 9448 quote."""
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'tools/v4')]
from canonical import content_hash
from release_gate_core import evaluate_release_gate

REPORT = 'docs/PENDING_SOURCE_BATCH1_AUTHOR_20261008.json'
PUBLISHED = {
    'H_15607_4_2_1_1': {'K_PEND_15607_4_2_1_1_ZONING_20261008': ('C_15607_4_2_1', 'direct'),
                        'K_PEND_15607_4_2_1_1_EXCEPTION_20261008': ('C_PEND_GB15607_4_2_2_20261008', 'supporting')},
    'H_15607_4_4_3_1': {'K_PEND_15607_4_4_3_1_BOOTH_20261008': ('C_15607_4_4_3', 'direct')},
    'H_15607_4_8_1_1': {'K_PEND_15607_4_8_1_1_REFERENCE_20261008': ('C_15607_4_8_1', 'direct'),
                        'K_PEND_15607_4_8_1_1_GB50058_5_4_1_20261008': ('C_GB50058_5_4_1', 'direct')},
    'H_15607_5_2_8_1': {'K_PEND_15607_5_2_8_1_REFERENCE_20261008': ('C_15607_5_2_8', 'direct'),
                        'K_PEND_15607_5_2_8_1_GROUNDING_20261008': ('C_15607_4_8_2', 'direct'),
                        'K_PEND_15607_5_2_8_1_ELECTRICAL_20261008': ('C_15607_4_7_2', 'direct')},
    'H_15607_6_1_1': {'K_PEND_15607_6_1_1_GB6514_7_3_2_1_20261008': ('C_PEND_GB6514_7_3_2_1_20261008', 'direct'),
                      'K_PEND_15607_6_1_1_REFERENCE_20261008': ('C_15607_6_1', 'direct')},
}
RETIRED = ('K_XLSX_WEB_B421EAC20EBDD91CB576FC83', 'K_XLSX_WEB_8AD4488F8A0347C8DDE6FEBF',
           'K_XLSX_WEB_B7C70D8364C74AFD84AADC0C', 'K_XLSX_WEB_90DB435011EFDD0313F168F8',
           'K_XLSX_WEB_AA82724434B0AA88213D5BE2')
KEPT = ('H_15607_4_4_1_1', 'H_15607_4_4_2_1', 'H_15607_5_2_1_1', 'H_15607_5_2_7_1')
MERGED, CANONICAL = 'H_AAD8D67536864E58BC01867E9C', 'H_67303D31915B4AC0A6902EB975'


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))


class PendingSourceBatch1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = evaluate_release_gate(ROOT / 'knowledge', date(2026, 10, 8))
        cls.report = load(REPORT)

    def test_five_bounded_rules_are_public_with_exact_original_clause_chains(self):
        for hid, links in PUBLISHED.items():
            with self.subTest(hazard=hid):
                hazard, review = load(f'knowledge/hazards/{hid}.json'), load(f'knowledge/reviews/hazards/{hid}.json')
                self.assertIn(hid, self.gate.eligible_hazards)
                self.assertEqual((hazard['lifecycle'], hazard['mode'], hazard['mergedInto']), ('active', 'direct', None))
                self.assertNotRegex(hazard['title'] + hazard['description'], r'未符合GB|的有关规定|的相关规定')
                self.assertIn('仅适用于粉末静电喷涂', hazard['conditions'])
                self.assertEqual(review['previousDefinition']['lifecycle'], 'proposed')
                self.assertTrue(review['remainingUnsupportedBranches'])
                self.assertIn('未经独立复核', review['notes'])
                actual = {link['id']: (link['clauseId'], link['role']) for link in
                          (load(f'knowledge/links/{kid}.json') for kid in links)}
                self.assertEqual(actual, links)
                for kid in links:
                    link = load(f'knowledge/links/{kid}.json')
                    self.assertEqual(link['hazardId'], hid)
                    self.assertEqual(link['applicability'], hazard['conditions'])
                    self.assertTrue(self.gate.links[kid]['ok'], kid)
                qualifying = set(self.gate.qualifying_links_by_hazard[hid])
                self.assertEqual(qualifying, {kid for kid, (_, role) in links.items() if role == 'direct'})

    def test_superseded_ocr_links_are_retired_and_rejected(self):
        for kid in RETIRED:
            link, review = load(f'knowledge/links/{kid}.json'), load(f'knowledge/reviews/links/{kid}.json')
            self.assertEqual((link['lifecycle'], review['decision']), ('retired', 'rejected'), kid)
            self.assertEqual(review['previousDefinition']['lifecycle'], 'proposed')
            self.assertNotIn(kid, self.gate.eligible_links)

    def test_quotes_follow_the_original_pages(self):
        quote = lambda cid: load(f'knowledge/clauses/{cid}.json')['quote']
        self.assertEqual(quote('C_15607_4_2_1'),
                         '喷粉区按的爆炸性粉尘环境危险区域划应按 GB 50058 的规定划分，各类喷粉室的爆炸性粉尘环境危险区域划分参见附录 A。')
        self.assertEqual(quote('C_15607_4_4_3'), '喷粉作业应在符合第 5 章规定的喷粉室内进行。')
        self.assertEqual(quote('C_PEND_GB6514_7_3_2_1_20261008'), '喷粉室应设机械通风和粉末净化回收装置。')
        self.assertTrue(quote('C_PEND_GB15607_4_2_2_20261008').startswith('喷粉区同时符合以下规定时，可划为非爆炸危险区域：'))
        welding = quote('C_GB9448_10')
        self.assertIn('辐射、含镉钎料、氟化物及噪声可能导致危害的地方，应设置适当的警告标志', welding)
        self.assertTrue(welding.endswith('焊接和切割区域应予以明确标明，并且应有必要的警告标志。'))
        self.assertNotIn('在可能造成危害的地方', welding)

    def test_welding_candidate_is_merged_without_changing_the_public_canonical(self):
        merged = load(f'knowledge/hazards/{MERGED}.json')
        self.assertEqual((merged['lifecycle'], merged['mergedInto']), ('superseded', CANONICAL))
        self.assertNotIn(MERGED, self.gate.eligible_hazards)
        self.assertIn(CANONICAL, self.gate.eligible_hazards)
        review = load('knowledge/reviews/links/K_474D0188C2AC738775C8F7.json')
        self.assertEqual(review['contextHashes']['clause'], content_hash(load('knowledge/clauses/C_GB9448_10.json')))
        self.assertEqual(review['contextHashes']['hazard'], content_hash(load(f'knowledge/hazards/{CANONICAL}.json')))

    def test_umbrella_and_unsourced_candidates_stay_unpublished(self):
        kept = {row['hazardId']: row for row in self.report['decisions'] if row['action'] == 'kept_proposed'}
        self.assertEqual(set(kept), set(KEPT))
        for hid in KEPT:
            self.assertEqual(load(f'knowledge/hazards/{hid}.json')['lifecycle'], 'proposed')
            self.assertNotIn(hid, self.gate.eligible_hazards)

    def test_report_states_author_self_check_and_pins_every_authored_file(self):
        self.assertEqual(self.report['reviewStage'], 'author_self_check_only')
        self.assertEqual(self.report['independentReview'], 'not_performed')
        self.assertEqual({row['hazardId'] for row in self.report['decisionsRequiringOwnerConfirmation']},
                         {'H_15607_4_2_1_1', 'H_15607_4_8_1_1'})
        for flag in ('siteFactsConfirmed', 'rectificationConfirmed', 'formalApproval', 'originalPdfsPublished'):
            self.assertIs(self.report[flag], False)
        self.assertEqual(sorted(self.report['authoredSha256']), self.report['authoredFiles'])


if __name__ == '__main__':
    unittest.main()
