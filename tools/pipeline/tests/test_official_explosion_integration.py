"""P08/P09 official-source boundaries; synthetic mutation tests are not site review."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from normative_content import content_text, validate_ordinary_clause_content
from build_unified_release import project_clause_content
from basis_refs import project_basis_reference
import release_gate_core as gate

H08 = 'H_GB3836_UNUSED_ENTRY'
H09 = 'H_GB3836_EX_D_MISSING_FASTENER'
C08 = 'C_GB3836_15_6_4_4'
K08 = 'K_GB3836_UNUSED_ENTRY_6_4_4'
INITIAL = ['K_GB3836_EX_D_INITIAL_B_1_A11', 'K_GB3836_EX_D_INITIAL_8']
MAINT = ['K_GB3836_EX_D_MAINT_A_1_A11', 'K_GB3836_EX_D_MAINT_5_7_1', 'K_GB3836_EX_D_MAINT_6_1']


def read(group, ident):
    return json.loads((ROOT / 'knowledge' / group / (ident + '.json')).read_text())


class OfficialExplosionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        report = json.loads((ROOT / 'docs/OFFICIAL_EXPLOSION_INTEGRATION_20261005.json').read_text())
        cls.state = {g: {} for g in ['laws', 'law-versions', 'clauses', 'hazards', 'links']}
        cls.state.update({'reviews/' + g: {} for g in list(cls.state)})
        for name in report['authoredFiles']:
            p = Path(name)
            group = '/'.join(p.parts[1:-1])
            if group in cls.state:
                obj = json.loads((ROOT / p).read_text())
                cls.state[group][obj.get('entityId', obj.get('id'))] = obj

    def evaluate(self, state=None, day='2026-10-05'):
        def load(_root, group):
            return copy.deepcopy((state or self.state)[group.replace('\\', '/')])
        with patch.object(gate, 'load_dir', load), patch.object(gate, 'load_reviews', load):
            return gate.evaluate_release_gate(ROOT / 'knowledge', date.fromisoformat(day))

    def test_complete_new_cohort_passes_current_gate_not_before_effective_day(self):
        self.assertEqual(len(self.state['laws']), 2)
        self.assertEqual(len(self.state['law-versions']), 2)
        self.assertEqual(len(self.state['clauses']), 8)
        self.assertEqual(len(self.state['hazards']), 2)
        self.assertEqual(len(self.state['links']), 6)
        for day in ['2025-08-01', '2026-10-05']:
            result = self.evaluate(day=day)
            self.assertEqual(result.eligible_hazards, {H08, H09})
            self.assertEqual(result.eligible_links, {K08, *INITIAL, *MAINT})
        result = self.evaluate(day='2025-07-31')
        self.assertEqual(result.eligible_hazards, set())
        self.assertEqual(result.eligible_links, set())

    def test_law_scope_exclusions_and_replacements(self):
        v15 = self.state['law-versions']['LV_STD_GB3836_15_2024']
        v16 = self.state['law-versions']['LV_STD_GB3836_16_2024']
        self.assertEqual(v15['replacesDocumentNumber'], 'GB/T 3836.15-2017')
        self.assertEqual(v16['replacesDocumentNumber'], 'GB/T 3836.16-2022')
        self.assertIn('医疗室', v15['scope'])
        for v in [v15, v16]:
            self.assertIn('煤矿井下', v['scope'])
            self.assertIn('自燃物质', v['scope'])
            self.assertEqual(v['effectiveDate'], '2025-08-01')
        self.assertIn('大气环境条件下', v16['scope'])

    def test_full_644_text_and_independent_intrinsic_safety_exceptions(self):
        c = self.state['clauses'][C08]
        self.assertEqual(c['contentParts'][0]['text'],
            '除仅包含一个本质安全电路的外壳外，外壳上未使用的引入孔应使用符合表9的封堵件封堵，并且应保持IP54的防护等级或者所在位置要求的防护等级，取二者之中的较高级别。\n对于隔爆外壳，管接头不应与封堵元件一起使用。')
        self.assertEqual(c['contentParts'][-1]['text'],
            '注：√表示允许使用。\na 如果只使用一个本质安全电路，则对电缆引入装置没有规定要求。\nb 只对EPL Gc级装置允许。')
        scope = self.state['links'][K08]['applicability']
        for text in ['仅包含一个本质安全电路的外壳排除', '认证设计中的呼吸、排液结构不是未用引入孔', 'IP54与所在位置要求取较高级别', '隔爆外壳不得管接头与封堵元件一起使用', '不能一律要求钢堵或一律排除塑料']:
            self.assertIn(text, scope)

    def test_table9_all_rows_columns_merged_cells_and_cross_references(self):
        c = self.state['clauses'][C08]
        table = c['contentParts'][1]
        self.assertEqual(table['columnCount'], 5)
        self.assertEqual(table['sourcePages'], [31])
        self.assertEqual(table['headerRows'][0][0]['rowSpan'], 2)
        self.assertEqual(table['headerRows'][0][1]['colSpan'], 4)
        self.assertEqual([x['text'] for x in table['headerRows'][1]],
                         ['Ex“d”\n（见6.4.5）', 'Ex“e”', 'Ex“n”', 'Ex“t”\n（见6.4.6）'])
        actual = [[x['text'] for x in row] for row in table['bodyRows']]
        expected = [
            ['Ex“d”','√','—','—','—'],
            ['Ex“e”','√','√','—','—'],
            ['Ex“i”（Ⅱ类ᵃ）','√','√','√（见7.3.4）','—'],
            ['Ex“i”（Ⅲ类ᵃ）','—','—','—','√（见7.3.4）'],
            ['Ex“m”','Ex“m”通常不适用于布线连接。连接的保护技术应适合所用的布线系统'],
            ['Ex“n”\n对Ex“nR”，另见6.4.7','√','√','√','—'],
            ['Ex“o”','Ex“o”通常不适用于布线连接。连接的保护技术应适合所用的布线系统'],
            ['Ex“p”（Ⅱ类）','√','√','√ᵇ','—'],
            ['Ex“p”（Ⅲ类）','—','—','—','√'],
            ['Ex“q”','Ex“q”通常不适用于布线连接。连接的保护技术应适合所用的布线系统'],
            ['Ex“s”','仅在证书条件允许的情况下'],
            ['Ex“t”','—','—','—','√'],
        ]
        self.assertEqual(actual, expected)
        for ix in [4,6,9,10]:
            self.assertEqual(table['bodyRows'][ix][1]['colSpan'], 4)
        r = self.state['reviews/clauses'][C08]
        self.assertEqual(validate_ordinary_clause_content(c, r), ['T_GB3836_15_2024_9'])
        self.assertEqual(c['quote'], content_text(c['contentParts']))
        self.assertEqual(project_clause_content(c)['contentParts'], c['contentParts'])

    def test_table_body_and_footnote_mutations_cannot_reuse_original_review(self):
        mutations = [
            lambda c: c.pop('contentParts'),
            lambda c: c['contentParts'][1]['bodyRows'].pop(),
            lambda c: c['contentParts'][1]['bodyRows'][7][3].update(text='√'),
            lambda c: c['contentParts'][-1].update(text='注：√表示允许使用。'),
            lambda c: c['contentParts'][0].update(text='所有开口必须钢堵。'),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                state = copy.deepcopy(self.state)
                mutate(state['clauses'][C08])
                self.assertNotIn(K08, self.evaluate(state).eligible_links)
                self.assertNotIn(H08, self.evaluate(state).eligible_hazards)
        c = copy.deepcopy(self.state['clauses'][C08]); c.pop('contentParts')
        r = copy.deepcopy(self.state['reviews/clauses'][C08]); r['reviewedContentHash'] = content_hash(c)
        ok, reasons = gate.gate_clause(c, r, True, True)
        self.assertFalse(ok)
        self.assertTrue(any('REQUIRED_TABLE_MISSING' in x for x in reasons))

    def test_single_p09_hazard_with_strict_ex_d_and_actual_absence_boundary(self):
        h = self.state['hazards'][H09]
        self.assertIn('Ex d/db隔爆型外壳', h['description'])
        self.assertIn('实际缺失', h['description'])
        for kid in INITIAL + MAINT:
            k = self.state['links'][kid]
            self.assertEqual(k['hazardId'], H09)
            for text in ['制造商和认证文件', '实际缺失', '照片遮挡或看不清不能推定缺失', '吊装孔', '接地点', '接地螺栓', '认证呼吸/排液结构', '非Ex d/db设备不能套本H']:
                self.assertIn(text, k['applicability'])

    def test_initial_and_in_service_methods_and_scopes_do_not_mix(self):
        for kid in INITIAL:
            scope = self.state['links'][kid]['applicability']
            self.assertIn('仅电气装置安装完成后和首次使用前的初始检查阶段', scope)
            self.assertIn('表B.1 A11的Ex“d”栏：物理检查为√', scope)
            self.assertNotIn('目视检查V为√', scope)
        for kid in MAINT:
            scope = self.state['links'][kid]['applicability']
            self.assertIn('本关联仅在役设备检查和维护阶段', scope)
            self.assertIn('物理检查D、C为√，目视检查V为√', scope)
            self.assertIn('不把目视检查等同于物理紧固核查', scope)
        b = self.state['reviews/clauses']['C_GB3836_15_B_1_A11']['sourceTableSelection']
        a = self.state['reviews/clauses']['C_GB3836_16_A_1_A11']['sourceTableSelection']
        self.assertFalse(a['wholeTableTranscribed']); self.assertFalse(b['wholeTableTranscribed'])
        self.assertEqual(b['checks'], [{'method':'物理检查','mark':'√'}])
        self.assertEqual(a['checks'], [{'method':'物理检查','grade':'D','mark':'√'}, {'method':'物理检查','grade':'C','mark':'√'}, {'method':'目视检查','grade':'V','mark':'√'}])
        self.assertEqual(a['columns'], ['Ex“d”'])

    def test_full_maintenance_clauses_keep_manufacturer_conditions_and_exceptions(self):
        q = self.state['clauses']['C_GB3836_16_5_7_1']['quote']
        for text in ['螺栓不透孔不应涂润滑油脂', '非金属刮刀和非腐蚀性清洗液', 'a）符合制造商文件的限值', 'b）制造时相关设备标准允许的最大值', 'c）修复后现场文件允许的最大值', '不能拆卸的接合面不必按照表A.1中A13和A16进行检查', '仅应使用按照制造商规定的零部件进行更换']:
            self.assertIn(text, q)
        q = self.state['clauses']['C_GB3836_16_6_1']['quote']
        self.assertIn('未经授权不能进行更换', q)
        self.assertTrue(q.endswith('说明书应经过设备检验机构批准。'))
        self.assertIn('来源于GB（GB/T）3836系列相应标准', self.state['clauses']['C_GB3836_15_8']['quote'])

    def test_per_link_scope_projection_is_lossless_and_separate(self):
        for kid in [K08] + INITIAL + MAINT:
            k = self.state['links'][kid]
            basis = project_basis_reference(k, 'c0000')
            self.assertEqual(basis['applicability'], k['applicability'])
            self.assertEqual(basis['linkId'], kid)
            self.assertEqual(basis['jurisdictionCode'], 'CN')
        self.assertNotEqual(self.state['links'][INITIAL[0]]['applicability'], self.state['links'][MAINT[0]]['applicability'])

    def test_modified_link_scope_or_type_cannot_reuse_review(self):
        for kid in [K08] + INITIAL + MAINT:
            state = copy.deepcopy(self.state)
            state['links'][kid]['applicability'] = 'All equipment at any phase'
            self.assertNotIn(kid, self.evaluate(state).eligible_links)
        state = copy.deepcopy(self.state)
        state['hazards'][H09]['description'] = 'Any visible hole is a missing bolt'
        self.assertNotIn(H09, self.evaluate(state).eligible_hazards)
        state = copy.deepcopy(self.state)
        for kid in [INITIAL[0], MAINT[0]]:
            del state['reviews/links'][kid]
        self.assertNotIn(H09, self.evaluate(state).eligible_hazards)

    def test_evidence_and_report_make_no_site_or_pdf_publication_claim(self):
        report = json.loads((ROOT / 'docs/OFFICIAL_EXPLOSION_INTEGRATION_20261005.json').read_text())
        for field in ['siteFactsConfirmed','rectificationConfirmed','formalApproval','originalPdfsPublished']:
            self.assertFalse(report[field])
        for eid in ['E_OFFICIAL_P08_P09_INSTALL_20261005','E_OFFICIAL_P09_MAINTENANCE_20261005']:
            e = read('evidence', eid)
            self.assertTrue(e['url'].startswith('https://openstd.samr.gov.cn/'))
            self.assertEqual(len(e['snapshotSha256']), 64)
            self.assertIn('原件不上传公共仓库', e['snapshotMeaning'])
        self.assertEqual(len(report['authoredFiles']), len(set(report['authoredFiles'])))
        self.assertTrue(all(p.endswith('.json') for p in report['authoredFiles']))
        self.assertTrue(all(not p.startswith(('source/', 'web/')) for p in report['authoredFiles']))


if __name__ == '__main__':
    unittest.main()
