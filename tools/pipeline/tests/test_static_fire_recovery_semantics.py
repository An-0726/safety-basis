"""Current scoped obligations, alternatives and exclusions from independent review."""
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
from residual_clause_cohort_fixture import pre_residual_repo_root
# Retain this dated recovery cohort's exact source and all original assertions.
ROOT = pre_residual_repo_root(ROOT)
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from release_gate_core import evaluate_release_gate

def read(kind, ident):
    return json.loads((KNOW / kind / (ident + '.json')).read_text())


class StaticFireRecoverySemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = evaluate_release_gate(KNOW, date(2026, 10, 4))

    def test_exact_nine_table_rows_without_invented_zone_two_classes(self):
        expected = [
            [('0区', 4), ('Ⅰ类', 1), ('3.0', 1), ('100', 1)],
            [('ⅡA类', 1), ('0.3', 1), ('50', 1)],
            [('ⅡB类', 1), ('0.3', 1), ('25', 1)],
            [('ⅡC类', 1), ('0.1', 1), ('4', 1)],
            [('1区', 4), ('Ⅰ类', 1), ('3.0', 1), ('100', 1)],
            [('ⅡA类', 1), ('3.0', 1), ('100', 1)],
            [('ⅡB类', 1), ('3.0', 1), ('100', 1)],
            [('ⅡC类', 1), ('2.0', 1), ('20', 1)],
            [('2区', 1), ('Ⅰ类', 1), ('3.0', 1), ('100', 1)],
        ]
        for cid in ('C_12158_4_2_3_4', 'C_12158_6_3_2'):
            clause = read('clauses', cid)
            table = next(part for part in clause['contentParts'] if part['type'] == 'table')
            self.assertEqual([[(cell['text'], cell['rowSpan']) for cell in row]
                              for row in table['bodyRows']], expected)
            self.assertTrue(all(cell['colSpan'] == 1 for row in table['bodyRows'] for cell in row))
            for token in ('如工艺需要', '必要时', '形成文件', '静电防护管理体系'):
                self.assertIn(token, clause['quote'])

    def test_resistivity_and_belt_paths_are_alternatives_with_exact_limits(self):
        self.assertEqual(read('clauses', 'C_12158_6_3_1')['quote'],
            '非金属材料的液体贮存罐、输送管道用于爆炸危险场所时，所用材料应满足表面电阻率小于1×10¹⁰Ω或体电阻率小于1×10⁸Ω·m，或采取其他静电防护措施。注：其他静电防护措施包括使用静电消除器，使用惰性气体保护等。')
        h = read('hazards', 'H_12158_6_3_1_1')
        for token in ('不小于1×10¹⁰Ω且', '不小于1×10⁸Ω·m', '又未采取'):
            self.assertIn(token, h['description'])
        belt = read('clauses', 'C_12158_7_6')['quote']
        for token in ('要求之一', '两面的表面电阻均小于3×10⁸Ω', 'GB/T 3836.26—2019中3.21',
                      '均小于7.5×10⁷Ω', '多层不同材料', '23℃±2℃', '50%±5%', '小于1×10⁹Ω'):
            self.assertIn(token, belt)
        self.assertIn('不得将三路径改为同时满足', read('hazards', 'H_12158_7_6_1')['conditions'])

    def test_five_restored_chains_and_the_false_glove_alias_remain_distinct(self):
        restored = {'H_12158_4_2_3_5_2', 'H_12158_6_3_1_1', 'H_12158_6_3_2_2',
                    'H_12158_7_6_1', 'H_12158_8_8_5_3'}
        self.assertTrue(restored <= self.gate.eligible_hazards)
        self.assertNotIn('H_12158_10_1_2', self.gate.eligible_hazards)
        aliases = read('hazards', 'H_12158_4_2_3_4_2')['aliases']
        self.assertFalse(restored & set(aliases))
        for hid in restored:
            self.assertIn('不适用于火炸药、电火工品、烟花爆竹', read('hazards', hid)['conditions'])

    def test_lighting_distance_keeps_exact_warehouse_branch_and_rejected_fallback(self):
        h = read('hazards', 'H052')
        self.assertEqual(h['description'], '既有仓储场所库房内堆放物品与照明灯之间的距离小于0.5m。')
        for token in ('既有仓储', '炸药仓库、花炮仓库', '第6.8条b项', '实测距离', '不由“灯具下方有物品”'):
            self.assertIn(token, h['conditions'])
        self.assertIn('H052', self.gate.eligible_hazards)
        kid = 'K_be5a0deab9619bd1579c758f'
        review = read('reviews/links', kid)
        self.assertEqual(review['decision'], 'rejected')
        self.assertNotIn(kid, self.gate.eligible_links)
        self.assertEqual(review['evidenceRefs'], ['E_CITATION_FIRELAW2021_20261002'])
        self.assertEqual(review['comparisonEvidenceRefs'], ['E_RECOVERY_XF1131_2014_20261004'])

    def test_mobile_duplicate_is_not_published_and_family_identity_is_version_aware(self):
        old = 'H_COM_MOBILE_ELECTRIC_CORD_SELECTION'
        target = 'H_8ECAE760F5A5413D8013602429'
        self.assertNotIn(old, self.gate.eligible_hazards)
        self.assertIn(target, self.gate.eligible_hazards)
        h = read('hazards', target)
        for token in ('交流1000V及以下', '直流1500V及以下', '护套软线均为允许选项',
                      '不覆盖固定配线', '不单凭本条认定行政违法'):
            self.assertIn(token, h['conditions'])
        family = read('laws', 'LF_STD_GBT13869')
        self.assertEqual(family['identityKey'], 'GB/T 13869|cn|推荐性国家标准')
        self.assertIn('2017版：中华人民共和国国家质量监督检验检疫总局', family['issuer'])
        self.assertIn('2026版：国家市场监督管理总局', family['issuer'])
        proof = read('reviews/laws', family['id'])
        self.assertNotIn('E_PRIV_GBT13869_2017', proof['evidenceRefs'])
        self.assertIn('E_PRIV_GBT13869_2017', proof['previousReview']['evidenceRefs'])
        self.assertEqual(read('law-versions', 'LV_STD_GBT13869_2017')['endDate'], '2027-02-01')
        self.assertEqual(read('law-versions', 'LV_STD_GBT13869_2026')['validityStatus'], 'upcoming')


if __name__ == '__main__':
    unittest.main()
