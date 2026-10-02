"""Public-source text, scope and precise containment regression tests."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest

from citation_cohort_fixture import FIXTURE, ADDED_IDS, pre_citation_gate
ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate
from field_profiles import public_projection
PINS = json.loads((Path(__file__).parent / 'fixtures' /
                   'public_citation_source_pins_20261002.json').read_text())


def read(kind, ident):
    return json.loads((KNOW / kind / f'{ident}.json').read_text(encoding='utf-8'))


class PublicCitationCorrectionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = evaluate_release_gate(KNOW, date(2026, 10, 2))

    def test_exact_source_files_and_preserved_previous_reviews(self):
        for rel, expected in PINS['sourceFileSha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), expected, rel)
        for rel, expected in PINS['previousReviews'].items():
            review = json.loads((ROOT / rel).read_text())
            self.assertEqual(review['previousReviewFileSha256'], expected['fileSha256'], rel)
            self.assertEqual(content_hash(review['previousReview']), expected['contentHash'], rel)
            entity = json.loads((ROOT / rel.replace('/reviews', '')).read_text())
            self.assertEqual(review['reviewedContentHash'], content_hash(entity), rel)
            if review['entityType'] == 'link':
                self.assertEqual(review['contextHashes'], {
                    'hazard': content_hash(read('hazards', entity['hazardId'])),
                    'clause': content_hash(read('clauses', entity['clauseId']))}, rel)

    def test_exact_fifteen_withdrawn_hazards_and_no_unrelated_loss(self):
        expected = {
            'H052', 'H053', 'H054', 'H055',
            'H_993643C76F7041BDA19B0C5EED',
            'H_8A733CAD776643E3B34B4D4689',
            'H_409ABC97960D46FBBF6AA54D28',
            'H_D98B4749D74246E2A3825D5B09',
            'H_524210530E054FE1BB1D918820',
            'H_D128C0FCC4844BD8BF5D8FAAF5',
            'H_6F7D6D7E28DD423B9F40AF8218',
            'H_C7284453E8E94532A44FC5F5EF',
            'H_F0D64F91542E4B0399D83D670D',
            'H_BC2436C8E5BE198BA82BB74B82_1',
            'H_1251ED2287FB47B6BDED9292D1',
        }
        delta = FIXTURE['gateSnapshots']['2026-10-02']
        self.assertEqual(set(delta['hazardsRemoved']), expected)
        self.assertEqual(delta['hazardsAdded'], [])
        for hid in expected:
            self.assertNotIn(hid, self.gate.eligible_hazards)
            self.assertEqual(read('reviews/hazards', hid)['decision'], 'pending')
            self.assertTrue(read('reviews/hazards', hid)['reason'])
        historical = pre_citation_gate(self.gate)
        self.assertEqual(historical.eligible_hazards - self.gate.eligible_hazards, expected)
        self.assertEqual((len(self.gate.eligible_hazards), len(self.gate.eligible_links)), (1665, 1809))

    def test_proposed_and_superseded_distance_links_are_never_auto_admitted(self):
        for kid in ('K_7EEF661BF4C8008AC0C070', 'K_1ED9FF46BEDB3CED1FA394',
                    'K_B9FF3B3BCC9404B8D71376', 'K_A02D92087BE34DF146E21F',
                    'K_F46299168EA56F465C4FAD1D'):
            self.assertEqual(read('links', kid)['lifecycle'], 'proposed')
            self.assertEqual(read('reviews/links', kid)['decision'], 'pending')
            self.assertNotIn(kid, self.gate.eligible_links)
        kid = 'K_822C6B6F2FF836A7505B9AC2'
        self.assertEqual(read('links', kid)['lifecycle'], 'superseded')
        self.assertEqual(read('reviews/links', kid)['decision'], 'superseded')
        self.assertNotIn(kid, self.gate.eligible_links)

    def test_exact_numbering_and_whole_distance_text(self):
        expected = '6.7 库房内储存物品应分类、分堆、限额存放。每个堆垛的面积不应大于150 m²。库房内主通道的宽度不应小于2 m。'
        for cid in ('C_XF1131_6_6', 'C_XLSX_FT_1488F0C3329AF5C8262E2AB2'):
            self.assertEqual(read('clauses', cid)['articlePath'], '第6.7条')
            self.assertEqual(read('clauses', cid)['quote'], expected)
        text = read('clauses', 'C_XF1131_6_8')['quote']
        self.assertTrue(text.startswith('6.8 库房内堆放物品应满足以下要求：'))
        self.assertIn('（人字屋架从横梁算起）', text)
        self.assertEqual(text.count('不小于'), 5)
        self.assertNotIn('150', text)
        self.assertNotIn('2 m', text)

    def test_special_equipment_and_jiangsu_consumers_keep_exact_paragraphs(self):
        expected = {
            'K_XLSX_FT_E43DDCADAAF192E7C887D2B4': ('C_D02C535701DC5CF8303999AB73', '第三十九条第二款'),
            'K_XLSX_FT_501C78507C483F5F7EF52C74': ('C_793B9FCC8767011C90B3C4AEA9', '第六十九条第三款'),
            'K_XLSX_FT_D94A59A3C1A9AF608CAF33FA': ('C_DB7FA5121B72C9FE0A33439033', '第二十八条第三款'),
        }
        for kid, (cid, branch) in expected.items():
            k = read('links', kid)
            self.assertEqual(k['clauseId'], cid)
            self.assertIn(branch, k['applicability'])
            self.assertIn(kid, self.gate.eligible_links)
        for kid in ('K_88A84E5C3800FA0B9ABEFC05', 'K_A4C9E3CAD774CFDEE897CE41',
                    'K_XLSX_FT_5240E43B6245EF1AA165854F', 'K_XLSX_NEW14_0F975F56E05C27DF746BB88D'):
            self.assertEqual(read('links', kid)['jurisdictionCode'], 'CN-32')

    def test_nanjing_exact_hundred_people_branch_is_not_part_time_only(self):
        special = read('links', 'K_H023_NJ_STAFFING_14')
        other = read('links', 'K_H023_NJ_STAFFING_15')
        self.assertEqual(special['jurisdictionCode'], 'CN-3201')
        self.assertEqual(other['jurisdictionCode'], 'CN-3201')
        self.assertIn('100至不足300至少1专职', other['applicability'])
        self.assertIn('100以上另须机构', other['applicability'])
        self.assertIn('不得二选一', read('hazards', 'H023')['measures'])
        self.assertTrue({'K_H023_NJ_STAFFING_14', 'K_H023_NJ_STAFFING_15'} <= self.gate.eligible_links)

    def test_three_new_clauses_keep_their_distinct_law_identity(self):
        for cid, lv in [('C_WAREHOUSE_FIRE_46', 'LV_REG_WAREHOUSE_FIRE_1990'),
                        ('C_GB50016_8_1_12', 'L025'), ('C_XF1131_8_10', 'L015')]:
            self.assertEqual(read('clauses', cid)['lawVersionId'], lv)
            self.assertTrue(read('clauses', cid)['sourceUrl'].startswith('https://'))
        self.assertIn('进入甲、乙类物品库区', read('clauses', 'C_WAREHOUSE_FIRE_46')['quote'])
        self.assertIn('本项不消费', read('links', 'K_XLSX_NEW14_05C4BD1DB3745B4FDA24316E')['applicability'])

    def test_extinguisher_body_text_is_not_explanatory_material_or_repair_cycle(self):
        c = read('clauses', 'C_XLSX_GB50444_5_3_1')
        self.assertEqual(c['quote'], '存在机械损伤、明显锈蚀、灭火剂泄露、被开启使用过或符合其他维修条件的灭火器应及时进行维修。')
        h = read('hazards', 'H_446213AC44A140D9B879B52981')
        self.assertIn('尚未达到GB55036', h['description'])
        self.assertNotIn('耐压强度', h['description'])
        self.assertIn('直接义务仅限未达到报废条件', h['conditions'])
        self.assertIn('5.3.1不在原强制性条文清单', read('reviews/law-versions', 'LV_STD_GB50444_2008')['reason'])
        self.assertIn('K_XLSX_GB50444_8D40A9941CD810B6909EDDF8', self.gate.eligible_links)

    def test_all_twenty_five_profiles_stay_publishable_without_profile_resigning(self):
        x = public_projection(KNOW, as_of=date(2026, 10, 2))
        self.assertEqual(len(x['public']['records']), 25)
        self.assertEqual(x['inventory']['excludedProfiles'], [])
        self.assertFalse(any(p.startswith('knowledge/field-profiles/') for p in PINS['sourceFileSha256']))

    def test_historical_projection_rejects_drift_and_retains_unknown_additions(self):
        modified = copy.deepcopy(self.gate)
        kid = 'K_XLSX_NEW14_E4704777D743EC11C3C851C3'
        modified.links[kid]['clauseId'] = 'C_UNREVIEWED'
        with self.assertRaises(AssertionError):
            pre_citation_gate(modified)
        modified = copy.deepcopy(self.gate)
        modified.eligible_hazards.add('H_UNREVIEWED')
        self.assertIn('H_UNREVIEWED', pre_citation_gate(modified).eligible_hazards)
        modified.eligible_hazards.remove('H001')
        self.assertNotIn('H001', pre_citation_gate(modified).eligible_hazards)


if __name__ == '__main__':
    unittest.main()
