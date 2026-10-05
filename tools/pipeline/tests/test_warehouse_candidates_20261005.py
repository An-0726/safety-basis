"""Bounded warehouse repair: exact branches, thresholds, exclusions and history."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate, gate_clause, gate_hazard_content, gate_link


def read(kind, ident):
    return json.loads((KNOW / kind / (ident + '.json')).read_text())


RESTORED = {
    'H053': 'K_1ED9FF46BEDB3CED1FA394',
    'H054': 'K_B9FF3B3BCC9404B8D71376',
    'H055': 'K_A02D92087BE34DF146E21F',
    'H_993643C76F7041BDA19B0C5EED': 'K_6EAF76314861ABC620BB9975',
    'H_D128C0FCC4844BD8BF5D8FAAF5': 'K_NEXT_WAREHOUSE_D128_XF1131_8_2_20261005',
}
REJECTED = [
    'K_9e6ba6262766224cc3d6e224', 'K_d9b8087219c0a33495f14d72',
    'K_d651b0312c6e6a0d36cde361', 'K_199989467c019b0789b69f66',
    'K_b5854a5f230a891b5fe35e8c', 'K_a6a1923c4d86007345fd7341',
    'K_F46299168EA56F465C4FAD1D', 'K_XLSX_NEW14_D1DA94F05E6955E3E9A73A2A',
    'K_XLSX_NEW14_EFD92528ABBFE27B1D100D87',
]


class WarehouseCandidateRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = evaluate_release_gate(KNOW, date(2026, 10, 5))

    def test_five_existing_ids_publish_only_their_specific_direct_basis(self):
        for hid, kid in RESTORED.items():
            with self.subTest(hazard=hid):
                self.assertIn(hid, self.gate.eligible_hazards)
                self.assertEqual(self.gate.qualifying_links_by_hazard[hid], [kid])
                self.assertEqual(read('links', kid)['role'], 'direct')
                self.assertIsNone(read('hazards', hid)['mergedInto'])

    def test_full_five_distance_clause_remains_intact(self):
        clause = read('clauses', 'C_XF1131_6_8')
        self.assertEqual(clause['quote'],
            '6.8 库房内堆放物品应满足以下要求：\n'
            'a）堆垛上部与楼板、平屋顶之间的距离不小于0.3 m（人字屋架从横梁算起）；\n'
            'b）物品与照明灯之间的距离不小于0.5 m；\n'
            'c）物品与墙之间的距离不小于0.5 m；\n'
            'd）物品堆垛与柱之间的距离不小于0.3 m；\n'
            'e）物品堆垛与堆垛之间的距离不小于1 m。')
        for hid, part, limit, obj in [('H053', 'c', '0.5', '物品与墙'),
                                      ('H054', 'd', '0.3', '物品堆垛与柱'),
                                      ('H055', 'e', '1', '物品堆垛与堆垛')]:
            h = read('hazards', hid)
            self.assertEqual(h['description'], f'既有仓储场所库房内{obj}之间的实测距离小于{limit}m。')
            for token in (f'仅消费第6.8条{part}项', '炸药仓库、花炮仓库',
                          '实测距离', '等于下限不因本项认定不符合', '室外堆场'):
                self.assertIn(token, h['conditions'])
            self.assertIn(f'不小于{limit}m', h['measures'])

    def test_classification_area_main_aisle_are_not_all_stack_distances(self):
        h = read('hazards', 'H_993643C76F7041BDA19B0C5EED')
        c = read('clauses', 'C_XF1131_6_6')
        self.assertEqual(c['articlePath'], '第6.7条')
        self.assertEqual(c['quote'], '6.7 库房内储存物品应分类、分堆、限额存放。每个堆垛的面积不应大于150 m²。库房内主通道的宽度不应小于2 m。')
        for token in ('未分类、分堆或限额存放', '大于150m²', '主通道宽度小于2m'):
            self.assertIn(token, h['description'])
        for token in ('150m²不是储量限额', '不覆盖“每个堆间搬运通道”', 'H053、H054、H055'):
            self.assertIn(token, h['conditions'])
        self.assertNotIn('间距', h['title'])
        self.assertNotIn('K_F46299168EA56F465C4FAD1D', self.gate.eligible_links)

    def test_each_handling_aisle_stays_unresolved_without_main_aisle_substitution(self):
        hid = 'H_F0D64F91542E4B0399D83D670D'
        self.assertEqual(read('hazards', hid)['description'], '库房堆垛之间未留出搬运通道。')
        self.assertEqual(read('reviews/hazards', hid)['decision'], 'pending')
        self.assertIn('均未逐字建立', read('reviews/hazards', hid)['reason'])
        self.assertNotIn(hid, self.gate.eligible_hazards)
        self.assertEqual(read('links', 'K_XLSX_NEW14_D1DA94F05E6955E3E9A73A2A')['lifecycle'], 'proposed')

    def test_lighting_clause_keeps_complete_conditional_text(self):
        cid = 'C_NEXT_XF1131_8_2_20261005'
        c = read('clauses', cid)
        self.assertEqual(c['quote'],
            '8.2 丙类固体物品的室内储存场所，不应使用碘钨灯和超过60 W以上的白炽灯等高温照明灯具。'
            '当使用日光灯等低温照明灯具和其他防燃型照明灯具时，应对镇流器采取隔热、散热等防火保护措施，确保安全。')
        self.assertEqual(c['lawVersionId'], 'L015')
        h = read('hazards', 'H_D128C0FCC4844BD8BF5D8FAAF5')
        for token in ('丙类固体', '室内储存', '超过60W的白炽灯', '镇流器', '隔热、散热'):
            self.assertIn(token, h['description'])
        for token in ('60W白炽灯不因功率本身', '不能仅凭这一点认定整体合格',
                      '不得把“超过60W以上的白炽灯”等同于所有超过60W的灯具',
                      '禁烟、用火和消防器材配置不由本H一并认证', '炸药仓库、花炮仓库'):
            self.assertIn(token, h['conditions'])

    def test_wrong_law_and_composite_links_remain_explicitly_rejected(self):
        for kid in REJECTED:
            rv = read('reviews/links', kid)
            self.assertEqual(rv['decision'], 'rejected')
            self.assertNotIn(kid, self.gate.eligible_links)
            self.assertTrue(rv['previousReview'])
            self.assertEqual(rv['reviewedContentHash'], content_hash(read('links', kid)))
        fire_law_kids = ['K_9e6ba6262766224cc3d6e224', 'K_d9b8087219c0a33495f14d72',
                         'K_d651b0312c6e6a0d36cde361', 'K_b5854a5f230a891b5fe35e8c',
                         'K_XLSX_NEW14_EFD92528ABBFE27B1D100D87']
        for kid in fire_law_kids:
            self.assertEqual(read('reviews/links', kid)['evidenceRefs'], ['E_CITATION_FIRELAW2021_20261002'])

    def test_prior_definitions_reviews_and_duplicate_stable_ids_survive(self):
        for hid in RESTORED:
            rv = read('reviews/hazards', hid)
            self.assertEqual(rv['previousDefinition']['id'], hid)
            self.assertEqual(rv['previousReview']['decision'], 'pending')
            self.assertEqual(rv['previousReview']['reviewedContentHash'], content_hash(rv['previousDefinition']))
        old = read('reviews/hazards', 'H_D128C0FCC4844BD8BF5D8FAAF5')['previousDefinition']
        self.assertIn('严禁烟火', old['title'])
        self.assertIn('照明和消防器材', old['description'])
        for hid in ['H_D3DD215E0D1E4D4A99E6D2D6A9', 'H_323DCD216820476B95E8153AE1']:
            self.assertEqual(read('hazards', hid)['lifecycle'], 'superseded')
            self.assertNotIn(hid, self.gate.eligible_hazards)
        self.assertEqual(read('hazards', 'H_323DCD216820476B95E8153AE1')['mergedInto'], 'H055')
        self.assertEqual(read('hazards', 'H_286F7049C36E470F8273F18889')['lifecycle'], 'proposed')

    def test_unknown_scope_mutations_are_not_silently_reapproved(self):
        for hid, kid in RESTORED.items():
            h = read('hazards', hid); rv = read('reviews/hazards', hid)
            self.assertTrue(gate_hazard_content(h, rv)[0])
            changed = copy.deepcopy(h); changed['conditions'] = '任何生产经营场所均适用。'
            self.assertFalse(gate_hazard_content(changed, rv)[0])
            k = read('links', kid); c = read('clauses', k['clauseId']); kr = read('reviews/links', kid)
            law = read('laws', 'LF_L015')
            self.assertTrue(gate_link(k, kr, h, c, law, True)[0])
            result = gate_link(k, kr, changed, c, law, True)
            self.assertFalse(result[0]); self.assertIn('BLOCK_REVIEW_CONTEXT_STALE:hazard_context_stale', result[1])
        cid = 'C_NEXT_XF1131_8_2_20261005'; c = read('clauses', cid)
        bad = copy.deepcopy(c); bad['quote'] = bad['quote'].replace('超过60 W以上', '60 W及以上')
        rv = read('reviews/clauses', cid); lv = read('law-versions', 'L015')
        self.assertTrue(gate_clause(c, rv, True, True, lv)[0])
        self.assertFalse(gate_clause(bad, rv, True, True, lv)[0])

    def test_shared_previously_finished_objects_are_unchanged(self):
        expected = {
            'hazards/H052': '1c2f7dcc87276e6083dd750fb32927cc23e44660b2d77226a9031471c4228ae5',
            'clauses/C_XF1131_6_6': '93a0d035a0d15607fdc0ba9f171e701e0b176e63fddbea4369b3843165cc6b18',
            'clauses/C_XF1131_6_8': '4cd4a1f415f1a8613a9ed4f31de8d3feb966f9ea68935a97c05a2cf121382de6',
            'law-versions/L015': '62cc3fbb5f0c5ff9c4cf6ccde4693fc301efbd425b81423381b37a87a20392f1',
            'evidence/E_RECOVERY_XF1131_2014_20261004': '8354aa35e97d20ec165994787a3681798ffa2b38453dc2a338c299622bff5044',
        }
        for key, digest in expected.items():
            kind, ident = key.split('/')
            self.assertEqual(content_hash(read(kind, ident)), digest)

    def test_currentness_review_does_not_adopt_known_bad_registry_metadata(self):
        e = read('evidence', 'E_NEXT_WAREHOUSE_XF1131_STATUS_20261005')
        self.assertEqual(e['retrievedAt'], '2026-10-05')
        self.assertIn('仅采用现行状态', e['notes'])
        self.assertIn('不复制2014-11-13日期', e['notes'])
        self.assertEqual(read('law-versions', 'L015')['effectiveDate'], '2014-03-01')


if __name__ == '__main__':
    unittest.main()
