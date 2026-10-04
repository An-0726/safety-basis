"""Contract tests for the 2026-10-04 source-grounded author reconstruction.
These validate explicit scope text and binding, not real-world violations.
"""
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash

def read(group, ident):
    return json.loads((ROOT / 'knowledge' / group / (ident + '.json')).read_text())

class ElectricalSourceRebuildTests(unittest.TestCase):
    def setUp(self):
        self.report = json.loads((ROOT / 'docs/electrical-source-rebuild-20261004.json').read_text())

    def test_new_scope_is_not_claimed_lost_payload_or_independent_review(self):
        self.assertTrue(self.report['oldCountsNotTargets'])
        self.assertIn('not_recovered', self.report['mode'])
        self.assertEqual(self.report['reviewStage'], 'author_verified_independent_review_pending')
        self.assertEqual(len(self.report['decisions']), 7)
        for d in self.report['decisions']:
            self.assertTrue(d['positiveCase'])
            self.assertTrue(d['negativeCase'])
            self.assertNotEqual(d['positiveCase'], d['negativeCase'])
            self.assertEqual(d['independentReview'], 'pending')

    def test_all_new_links_bind_exact_hazard_clause_and_scope(self):
        for d in self.report['decisions']:
            h = read('hazards', d['hazardId'])
            self.assertEqual(h['id'], d['hazardId'])
            r = read('reviews/hazards', h['id'])
            self.assertEqual(r['reviewedContentHash'], content_hash(h))
            for kid in d['linkIds']:
                k = read('links', kid); c = read('clauses', k['clauseId'])
                kr = read('reviews/links', kid)
                self.assertEqual(kr['reviewedContentHash'], content_hash(k))
                self.assertEqual(kr['contextHashes'], {'hazard': content_hash(h), 'clause': content_hash(c)})
                self.assertIn(h['conditions'], k['applicability'])
                self.assertIn(d['boundary'], k['applicability'])
                for eid in kr['evidenceRefs']:
                    self.assertEqual(read('evidence', eid)['tier'], 'authoritative-public')

    def test_tool_period_and_mark_are_distinct_with_full_table(self):
        h = read('hazards', 'H_CF_GEN_13')
        m = read('hazards', 'H_GBT3787_PERIODIC_CHECK_MARK')
        self.assertNotIn('未粘贴', h['title'])
        self.assertIn('不以缺少合格标识', h['conditions'])
        self.assertIn('前提为经定期检查合格', m['conditions'])
        q = read('clauses', 'C_GBT3787_2017_6_3')['quote']
        for s in ('每年至少检查一次', '湿热', '梅雨季节前', '500 V兆欧表', '——基本绝缘；2', '——加强绝缘；7', '隔离的金属零件之间；2', '隔离的金属零件与壳体之间；5', '工具编号', '检查单位名称或标记', '检查人员姓名或标记', '有效日期'):
            self.assertIn(s, q)
        v = read('law-versions', 'LV_STD_GBT3787_2017')
        self.assertEqual(v['endDate'], '2027-02-01')
        self.assertEqual(v['supersededEffectiveDate'], '2027-02-01')
        self.assertEqual(read('links', 'K_CF_GEN_13_C_0C94FB24040EB78218141DD12F')['lifecycle'], 'superseded')
        self.assertEqual(read('reviews/links', 'K_CF_GEN_13_C_0C94FB24040EB78218141DD12F')['decision'], 'rejected')

    def test_construction_box_not_all_metal_cabinet_doors(self):
        h = read('hazards', 'H_JGJT46_2024_BOX_PE')
        for s in ('施工现场临时用电', '电源中性点直接接地', '220V/380V', '三相四线制', '不向所有工厂固定配电箱外推'):
            self.assertIn(s, h['conditions'])
        q = read('clauses', 'C_JGJT46_2024_4_1_12')['quote']
        self.assertIn('黄/绿组合颜色软绝缘导线', q)
        self.assertNotIn('4mm', q); self.assertNotIn('4 mm', q)
        prior = read('hazards', 'H_43C6C076F9FC456DB09138A19A')
        self.assertIn('仅适用于装有电器', prior['conditions'])
        self.assertEqual(read('hazards', 'H_5565236C0E354D5D8428BC1DEB')['lifecycle'], 'superseded')

    def test_smoke_window_height_is_conditional_and_last_sentence_retained(self):
        h = read('hazards', 'H_GB51251_MANUAL_SMOKE_WINDOW')
        self.assertIn('普通通风窗不适用', h['conditions'])
        self.assertIn('高位且不便直接开启', h['conditions'])
        q = read('clauses', 'C_GB51251_2017_4_3_6')['quote']
        for s in ('1.3m～1.5m', '大于9m', '大于2000m²', '集中手动开启装置和自动开启设施'):
            self.assertIn(s, q)
        self.assertEqual(read('hazards', 'H_COM_SMOKE_WINDOW_CONTROL')['mergedInto'], 'H025')

    def test_cylinder_register_is_not_statutory_device_registration(self):
        h = read('hazards', 'H_GBT34525_CYLINDER_REGISTER')
        for s in ('气瓶出入库', '不是特种设备法定使用登记', '0.4 L～3000 L', '0.2 MPa～35 MPa', '车用气瓶'):
            self.assertIn(s, h['conditions'])
        q = read('clauses', 'C_GBT34525_2017_8_2_12')['quote']
        for s in ('气体名称', '气瓶编号', '出入库日期', '使用单位', '作业人'):
            self.assertIn(s, q)

    def test_cylinder_alarm_does_not_add_ups_to_all_detectors(self):
        h = read('hazards', 'H_GBT34525_CYLINDER_STORE_ALARM')
        self.assertIn('有毒、可燃气体库房和氧气及惰性气体库房', h['conditions'])
        self.assertNotIn('UPS', h['measures'])
        self.assertIn('不能附加给每个探测器', h['note'])
        self.assertNotIn('UPS', read('clauses', 'C_GBT34525_2017_8_2_8')['quote'])

    def test_lightning_ordinary_and_explosive_periods_do_not_become_major_criteria(self):
        h = read('hazards', 'H_89016FC0F3E849C2B8B8755C35')
        self.assertIn('投入使用后的', h['conditions'])
        self.assertIn('一般接地装置检测', h['conditions'])
        self.assertIn('普通检测义务', h['note'])
        self.assertIn('不提前应用2026-11-01', h['note'])
        q = read('clauses', 'C_CMA44_2025_13')['quote']
        self.assertIn('每年检测一次', q)
        self.assertIn('对爆炸和火灾危险环境场所', q)
        self.assertIn('每半年检测一次', q)
        self.assertIn(h['id'], self.report['previousDefinitions'])

    def test_ppe_remains_bounded_and_hydrant_unverified_is_deferred(self):
        p = read('hazards', 'H_COM_INSULATING_PPE_TEST')
        self.assertIn('国家规定应定期强制检验', p['conditions'])
        self.assertNotIn('半年', p['conditions'])
        d = next(x for x in self.report['deferred'] if x['topic'].startswith('室内消火栓'))
        self.assertIn('报批稿', d['reason'])
        self.assertFalse((ROOT / 'knowledge/hazards/H_GB50974_HOSE_PLACEMENT.json').exists())

    def test_version_gate_blocks_expired_2017_standard(self):
        from datetime import date
        from release_gate_core import gate_law_version
        v = read('law-versions', 'LV_STD_GBT3787_2017')
        r = read('reviews/law-versions', v['id'])
        self.assertTrue(gate_law_version(v, r, True, date(2027, 1, 31))[1])
        self.assertFalse(gate_law_version(v, r, True, date(2027, 2, 1))[1])
        v = read('law-versions', 'LV_CMA_LIGHTNING_MANAGEMENT_2025')
        r = read('reviews/law-versions', v['id'])
        self.assertTrue(gate_law_version(v, r, True, date(2026, 10, 31))[1])
        self.assertFalse(gate_law_version(v, r, True, date(2026, 11, 1))[1])

    def test_all_authored_hazards_and_links_pass_current_source_gate(self):
        from datetime import date
        from release_gate_core import evaluate_release_gate
        gate = evaluate_release_gate(str(ROOT / 'knowledge'), date(2026, 10, 4))
        for row in self.report['decisions']:
            self.assertIn(row['hazardId'], gate.eligible_hazards)
            for kid in row['linkIds']:
                self.assertIn(kid, gate.eligible_links)

    def test_scope_quote_and_baseline_history_corrections(self):
        self.assertIn('基本安全技术要求', read('clauses', 'C_GBT34525_2017_1')['quote'])
        old = self.report['previousDefinitions']['K_CF_GEN_13_C_0C94FB24040EB78218141DD12F review']
        self.assertEqual(old['contextHashes']['hazard'], 'ad8bd56b119df10cc3e62e254b4786c160d9333a252506100f7c822a34e9a079')
        self.assertEqual(self.report['previousDefinitions']['H_CF_GEN_13 review']['reviewedContentHash'], old['contextHashes']['hazard'])

    def test_browser_fixture_pins_and_rejects_wrong_basis_fields(self):
        import copy
        sys.path.insert(0, str(ROOT / 'tools/browser'))
        from electrical_candidate_acceptance import load_expectations, validate_source_pins, validate_projection
        f = load_expectations(); self.assertEqual(validate_source_pins(f, ROOT)['basisLinks'], 10)
        actual = {'details': [{'id':r['id'], 'hazard':copy.deepcopy(r['hazard']), 'bases':copy.deepcopy(r['bases'])} for r in f['records']]}
        self.assertEqual(validate_projection(f, actual)['hazards'], 7)
        for key, value in [('applicability', 'all locations'), ('quote', 'incomplete quote'), ('sourceUrl', 'https://example.invalid'), ('linkId', 'K_WRONG')]:
            with self.subTest(key=key):
                bad=copy.deepcopy(actual); bad['details'][0]['bases'][0][key]=value
                with self.assertRaises(AssertionError): validate_projection(f,bad)

if __name__ == '__main__':
    unittest.main()
