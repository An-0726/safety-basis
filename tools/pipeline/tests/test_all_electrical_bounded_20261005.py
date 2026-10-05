"""Focused regressions for the 2026-10-05 electrical/signs author batch.

This checks content bounds and immutable predecessor bytes; it is not an
independent legal review or a finding about a particular site.
"""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
K = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate

def get(group, ident):
    return json.loads((K / group / (ident + '.json')).read_text())

class ElectricalBoundedBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT / 'docs/all-electrical-bounded-author-20261005.json').read_text())
        cls.gate = evaluate_release_gate(K, datetime.date(2026, 10, 5))

    def test_authored_file_hashes_and_exact_predecessor_bytes(self):
        for path, sha in self.report['authoredSha256'].items():
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists())
                self.assertEqual(len(sha), 64)
                self.assertTrue(all(c in '0123456789abcdef' for c in sha))
        for path, old in self.report['beforeFiles'].items():
            if old['existed']:
                self.assertEqual(hashlib.sha256(old['fileTextUtf8'].encode()).hexdigest(), old['sha256'])
                self.assertIsInstance(json.loads(old['fileTextUtf8']), dict)

    def test_modified_hazards_preserve_aliases_and_keywords(self):
        for path, old in self.report['beforeFiles'].items():
            if path.startswith('knowledge/hazards/') and old['existed']:
                prior = json.loads(old['fileTextUtf8'])
                now = json.loads((ROOT / path).read_text())
                for field in ('aliases', 'keywords'):
                    self.assertEqual(now.get(field), prior.get(field), (path, field))

    def test_new_reviews_bound_to_entities_and_contexts(self):
        for path in self.report['authoredFiles']:
            if path.startswith('knowledge/reviews/'):
                r = json.loads((ROOT / path).read_text())
                group = Path(path).parts[-2]
                obj = get(group, r['entityId'])
                self.assertEqual(r['reviewedContentHash'], content_hash(obj))
                if group == 'links':
                    self.assertEqual(r['contextHashes']['hazard'], content_hash(get('hazards', obj['hazardId'])))
                    self.assertEqual(r['contextHashes']['clause'], content_hash(get('clauses', obj['clauseId'])))

    def test_bounded_active_definitions_pass_content_gate(self):
        for d in self.report['decisions']:
            if d['action'] == 'bounded_existing_stable_id':
                self.assertIn(d['hazardId'], self.gate.eligible_hazards)
                self.assertTrue(d['positiveCase'])
                self.assertTrue(d['negativeCase'])

    def test_unproven_compound_candidates_are_not_wholly_admitted(self):
        for hid in ('H_1507C0C16EB84487BA78230E0D', 'H_9306B9A1C86541D58647D2F5C9',
                    'H_E992B4486A6E43C791FBDFE919', 'H_C30C57E1211A46808D790A7D03'):
            self.assertNotIn(hid, self.gate.eligible_hazards)
        for m in self.report['branchMappings']:
            self.assertFalse(m['wholeCandidateApproved'])

    def test_mechanical_protection_is_design_not_universal_steel_pipe(self):
        h = get('hazards', 'H030')
        self.assertIn('设计', h['conditions'])
        self.assertIn('1000 V', h['conditions'])
        self.assertIn('不一律要求穿钢管', h['measures'])
        h = get('hazards', 'H_2F1B0A9321E844B98E16A6A3CA')
        for exception in ('Ⅱ类设备', '电气分隔', '特低电压供电', '非导电场所', '不接地等电位联结'):
            self.assertIn(exception, h['conditions'])

    def test_static_resistance_and_area_are_not_interchanged(self):
        h = get('hazards', 'H_12158_4_2_2_3_1')
        self.assertIn('大于100Ω', h['description'])
        self.assertIn('非静电泄漏电阻', h['conditions'])
        k = get('links', 'K_XLSX_WEB_H_12158_7_1_1')
        self.assertEqual(k['clauseId'], 'C_12158_7_1')
        self.assertIn('应大于20cm²', get('clauses', k['clauseId'])['quote'])
        self.assertIn('不大于20cm²', get('hazards', k['hazardId'])['description'])
        self.assertIn('不适用于仅金属与金属连接', get('hazards', k['hazardId'])['conditions'])

    def test_powder_duct_clause_is_exact_single_sentence(self):
        c = get('clauses', 'C_XLSX_WEB_EC95C5694483BC8D1A74E491')
        self.assertEqual(c['quote'], '含粉尘的排风管道应采用法兰连接并进行静电跨接。')
        self.assertIn('仅参照执行', get('hazards', 'H_15607_6_7_1')['conditions'])

    def test_recommended_machinery_standard_has_all_exclusions(self):
        h = get('hazards', 'H_GBT47236_4_2_2_2')
        for boundary in ('设计、制造和验收', '压铸机和压铸单元', '挤压铸造机', '旋压设备', '连续或半连续铸造机', '推荐性'):
            self.assertIn(boundary, h['conditions'])
        self.assertIn('能够设置防护的部件不得用涂色替代防护', h['measures'])
        self.assertIn('2027-02-01', get('hazards', 'H071')['conditions'])

    def test_jurisdiction_and_publicity_without_monthly_approval(self):
        for kid in ('K_XLSX_FT_A3883508D9D829ADA841C9B6', 'K_PHASE6_91E48D8B3B4CA5FC5506FD76',
                    'K_PHASE12_EXACT_586A2C2C04BECBBDB3D9'):
            k = get('links', kid)
            self.assertEqual(k['jurisdictionCode'], 'CN-32')
            self.assertIn('江苏', k['applicability'])
            self.assertIn('另有规定', k['applicability'])
        h = get('hazards', 'H_00DB7A50FF994B5DB5470A3B03')
        for forbidden in ('每月', '审核后', '审批'):
            self.assertNotIn(forbidden, h['measures'])
        self.assertIn('可以', h['measures'])

    def test_spray_booth_grounding_preserves_objects_and_separate_thresholds(self):
        c = get('clauses', 'C_GB14444_5_5_1')
        for phrase in ('所有导电部件', '金属排气管', '喷涂设备', '采用静电喷涂的工件', '供漆容器', '输漆管路', '专设的静电接地体', '不大于100Ω', '带电区对地的总泄漏电阻值', '不大于1×10⁶Ω'):
            self.assertIn(phrase, c['quote'])
        h = get('hazards', 'H_CFDF32963AFD42B79932BE1A61')
        self.assertIn('可燃、易燃液体涂料', h['conditions'])
        self.assertIn('设计、制造、安装、调试、检验、运行和维护', h['conditions'])
        self.assertIn('不把非静电喷涂工件一律纳入', h['conditions'])
        self.assertNotIn('100Ω', h['description'])
        self.assertNotIn('10⁶Ω', h['description'])
        self.assertIn(h['id'], self.gate.eligible_hazards)
        k = get('links', 'K_ALL_ELECTRICAL_CFDF32963AFD42B79932BE1A61_20261005')
        self.assertEqual(k['clauseId'], c['id'])
        self.assertEqual(k['hazardId'], h['id'])

    def test_site_selection_mirror_does_not_grant_formal_admission(self):
        for group, ident in (
            ('clauses', 'C_GB50187_3_0_6'),
            ('hazards', 'H_4DAD0BA8DA8A454897E2954776'),
            ('links', 'K_XLSX_WEB_H_4DAD0BA8DA8A454897E2954776')):
            self.assertEqual(get(group, ident)['lifecycle'], 'proposed')
            r = get('reviews/' + group, ident)
            self.assertEqual(r['decision'], 'pending')
            self.assertEqual(r['sourceAdmission'], 'official-full-original-required')
            self.assertIn('withdrawnAuthorAttemptHashes', r)
        self.assertNotIn('H_4DAD0BA8DA8A454897E2954776', self.gate.eligible_hazards)
        self.assertNotIn('H_A426878B99904B9F802AA6BE47', self.gate.eligible_hazards)

    def test_safety_law_warning_does_not_include_labels_or_maximum_grade(self):
        h = get('hazards', 'H_B30EDC5AFD774470A555F9B715')
        self.assertIn('较大危险因素', h['conditions'])
        self.assertIn('不含包装GHS标签', h['conditions'])
        self.assertNotIn('最高等级', h['measures'])
        self.assertEqual(
            get('clauses', 'C_XLSX_FT_0A0BC6D714EBEE8BE88DC97C')['quote'],
            '第三十五条 生产经营单位应当在有较大危险因素的生产经营场所和有关设施、设备上，设置明显的安全警示标志。')

if __name__ == '__main__':
    unittest.main()
