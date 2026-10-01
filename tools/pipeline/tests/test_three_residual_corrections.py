"""Exact provenance and sixteen bounded semantic regressions for three repairs.

These assertions guard the reviewed wording, actor, scope and logical branches.
They are not an on-site legal adjudication engine or a whole-corpus approval.
"""
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' /
                     'three_residual_corrections_20260930.json').read_text(encoding='utf-8'))
SPACE = 'H_48B66BAC_12_1'
PRODUCTION = 'H_1AD0D576979A2F4717DA1E73D1_2'
SCRAP = 'H_8300469D69145B0731074A2CC4_1'


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def hazard(hid):
    return read(f'knowledge/hazards/{hid}.json')


class ThreeResidualProvenanceTests(unittest.TestCase):
    def test_exact_six_entity_records_and_unchanged_fields(self):
        self.assertEqual(len(FIXTURE['entities']), 6)
        for row in FIXTURE['entities']:
            with self.subTest(path=row['path']):
                actual = read(row['path'])
                self.assertEqual(actual, row['record'])
                self.assertEqual(content_hash(actual), row['contentHash'])
                self.assertNotEqual(row['oldContentHash'], row['contentHash'])
                self.assertEqual(hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest(),
                                 row['fileSha256'])
                for field, value in row['unchangedFields'].items():
                    self.assertEqual(actual[field], value)
                self.assertNotIn('measures', row['modifiedFields'])
        self.assertEqual(sum(len(row['modifiedFields']) for row in FIXTURE['entities']), 14)

    def test_exact_six_substantive_reviews_and_context_bindings(self):
        self.assertEqual(len(FIXTURE['reviews']), 6)
        for row in FIXTURE['reviews']:
            with self.subTest(path=row['path']):
                actual = read(row['path'])
                entity = read(row['path'].replace('/reviews', ''))
                self.assertEqual(actual, row['record'])
                self.assertEqual(hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest(),
                                 row['fileSha256'])
                self.assertEqual(actual['reviewedContentHash'], content_hash(entity))
                self.assertEqual(actual['reviewer'], 'Codex三条残余独立法律语义复核20260930')
                self.assertEqual(actual['decision'], 'verified')
                self.assertIn('本次审核限', actual['notes'])
                self.assertEqual(len(actual['evidenceRefs']), len(set(actual['evidenceRefs'])))
                if actual['entityType'] == 'link':
                    self.assertEqual(entity['role'], 'direct')
                    self.assertEqual(entity['applicability'], hazard(entity['hazardId'])['conditions'])
                    self.assertEqual(actual['contextHashes'], {
                        'hazard': content_hash(hazard(entity['hazardId'])),
                        'clause': content_hash(read(f"knowledge/clauses/{entity['clauseId']}.json"))})

    def test_evidence_exactly_matches_law_and_article_not_other_standards(self):
        self.assertEqual(len(FIXTURE['evidence']), 9)
        evidence = {row['id']: row for row in FIXTURE['evidence']}
        for eid, row in evidence.items():
            obj = read(f'knowledge/evidence/{eid}.json')
            self.assertEqual(obj, row['record'])
            self.assertEqual(hashlib.sha256((ROOT / 'knowledge/evidence' /
                                            f'{eid}.json').read_bytes()).hexdigest(), row['fileSha256'])
            self.assertIn(row['usedScope']['law'], ('MEM13', 'TSELAW'))
            self.assertEqual(obj['tier'], 'authoritative-public')
        for row in FIXTURE['reviews']:
            review = read(row['path'])
            expected_law = 'MEM13' if review['entityId'] in (
                SPACE, 'K_XLSX_FT_577A6055EF9B053BBAF2DA7F') else 'TSELAW'
            for eid in review['evidenceRefs']:
                self.assertEqual(evidence[eid]['usedScope']['law'], expected_law)
        space = read(f'knowledge/reviews/hazards/{SPACE}.json')['evidenceRefs']
        self.assertIn('E_XLSX_FT_52EE92815856956C92B3D4CC', space)  # Article 7
        self.assertIn('E_XLSX_FT_F8BFF2631FB9A86595C65DEF', space)  # Article 14

    def test_three_measures_are_byte_for_byte_preserved(self):
        self.assertEqual(set(FIXTURE['preservedMeasures']), {SPACE, PRODUCTION, SCRAP})
        for hid, text in FIXTURE['preservedMeasures'].items():
            self.assertEqual(hazard(hid)['measures'], text)

    def test_dated_gate_keeps_three_targets_and_existing_containment(self):
        gate = evaluate_release_gate(ROOT / 'knowledge', date(2026, 9, 30))
        for hid in (SPACE, PRODUCTION, SCRAP):
            self.assertIn(hid, gate.eligible_hazards)
        for row in FIXTURE['entities']:
            if '/links/' in row['path']:
                self.assertIn(row['record']['id'], gate.eligible_links)
        # Current projection additionally excludes the four independently reviewed
        # MEM10 wrong-source chains. The new containment suite reconstructs the
        # unchanged historical 1657/1791/1340 snapshot from preserved reviews.
        self.assertEqual(len(gate.eligible_hazards), 1653)
        self.assertEqual(len(gate.eligible_links), 1787)
        self.assertNotIn('H_12158_10_1_2', gate.eligible_hazards)

    def test_three_templates_removed_and_short_space_title(self):
        self.assertEqual(hazard(SPACE)['title'],
                         '工贸企业可能产生有毒物质的有限空间未按规定采取物理隔离措施')
        self.assertNotIn('不相容物质', hazard(SPACE)['description'])
        self.assertNotIn('现场参数、设置或状态', hazard(PRODUCTION)['description'])
        self.assertNotIn('安全防护、识别、监测或应急', hazard(SCRAP)['description'])
        self.assertEqual(len(FIXTURE['boundaryCases']), 16)


class ThreeResidualSemanticBoundaryTests(unittest.TestCase):
    def test_01_space_requires_industry_and_definition(self):
        text = hazard(SPACE)['conditions']
        self.assertIn('第二条所称工贸企业中符合第三条定义', text)
        self.assertIn('冶金、有色、建材、机械、轻工、纺织、烟草、商贸',
                      FIXTURE['statutoryText']['MEM13_2']['fullText'])
        self.assertIn('未被设计为固定工作场所', FIXTURE['statutoryText']['MEM13_3']['fullText'])

    def test_02_space_requires_possible_toxic_substances(self):
        self.assertIn('且可能产生有毒物质的有限空间', hazard(SPACE)['conditions'])
        self.assertEqual(hazard(SPACE)['places'], ['工贸企业可能产生有毒物质的有限空间'])

    def test_03_current_safe_reading_does_not_remove_possible_toxic_scope(self):
        self.assertIn('可能产生有毒物质', hazard(SPACE)['description'])
        for text in (hazard(SPACE)['description'], hazard(SPACE)['conditions']):
            self.assertNotIn('有毒气体超标的有限空间', text)
            self.assertNotIn('检测超标时才', text)

    def test_04_normal_prework_opening_does_not_prove_absent_isolation(self):
        text = hazard(SPACE)['conditions']
        self.assertIn('监护人员按第十二条在作业前正常解除物理隔离的，不得仅凭入口开放认定本项隐患', text)
        self.assertIn('解除隔离不等于获准作业', text)
        self.assertIn('第七条作业审批', text)
        self.assertIn('第十四条“先通风、再检测、后作业”', text)
        for invented in ('审批后方可解除', '解除后方可审批', '审批前解除'):
            self.assertNotIn(invented, text)

    def test_05_actual_unauthorized_entry_is_not_a_missing_barrier_prerequisite(self):
        text = hazard(SPACE)['description']
        self.assertIn('未落实用于防止人员未经审批进入的', text)
        self.assertNotIn('且已发生未经审批进入', text)
        review = read(f'knowledge/reviews/hazards/{SPACE}.json')
        self.assertIn('不以实际发生未经审批进入作为缺失隔离的必要前提', review['reason'])

    def test_06_production_plan_alone_is_not_actual_illegal_production(self):
        text = hazard(PRODUCTION)['conditions']
        self.assertIn('判定本项应有实际生产活动事实', text)
        self.assertIn('仅有拟生产计划', text)
        self.assertIn('不足以据此认定已发生本项违法生产', text)

    def test_07_user_registration_or_site_state_does_not_prove_production(self):
        self.assertIn('仅有使用登记、使用现场参数和设备状态，不足以据此认定',
                      hazard(PRODUCTION)['conditions'])
        self.assertEqual(hazard(PRODUCTION)['places'], ['特种设备生产单位及生产活动'])

    def test_08_actual_design_is_production_even_without_finished_product(self):
        text = hazard(PRODUCTION)['conditions']
        self.assertIn('生产包括设计、制造、安装、改造、修理', text)
        self.assertIn('已实际开展设计等法定生产活动的，不因尚未制造成品而排除适用', text)
        self.assertIn('生产（包括设计、制造、安装、改造、修理）',
                      FIXTURE['statutoryText']['TSELAW_2']['fullText'])

    def test_09_safety_noncompliance_is_not_excused_by_energy_compliance(self):
        self.assertIn('不符合适用的安全性能要求或能效指标', hazard(PRODUCTION)['description'])
        self.assertIn('不以安全性能与能效同时不符合为前提', hazard(PRODUCTION)['conditions'])

    def test_10_applicable_energy_noncompliance_is_not_excused_by_safe_performance(self):
        text = hazard(PRODUCTION)['conditions']
        self.assertIn('适用安全技术规范、相关标准中的安全性能要求或能效指标不符合项', text)
        self.assertNotIn('安全性能与能效均不符合才', text)

    def test_11_state_elimination_is_an_independent_production_branch(self):
        self.assertIn('或者属于国家明令淘汰的特种设备', hazard(PRODUCTION)['description'])
        self.assertIn('或者设备与国家明令淘汰规定的匹配情况', hazard(PRODUCTION)['conditions'])
        self.assertIn('国家明令淘汰的设备不得继续生产', hazard(PRODUCTION)['measures'])

    def test_12_serious_hazard_with_repair_value_does_not_satisfy_first_scrap_branch(self):
        text = hazard(SCRAP)['description']
        self.assertIn('存在严重事故隐患且无改造、修理价值，或者', text)
        self.assertNotIn('存在严重事故隐患或者无改造', text)

    def test_13_no_repair_value_alone_does_not_satisfy_first_scrap_branch(self):
        self.assertIn('（一）存在严重事故隐患且无改造、修理价值', hazard(SCRAP)['conditions'])
        self.assertNotIn('存在严重事故隐患或无改造', hazard(SCRAP)['conditions'])

    def test_14_other_applicable_technical_scrap_condition_is_independent(self):
        text = hazard(SCRAP)['conditions']
        self.assertIn('须确认以下任一报废条件', text)
        self.assertIn('（二）达到适用安全技术规范规定的其他报废条件', text)
        self.assertIn('或者达到安全技术规范规定的其他报废条件', hazard(SCRAP)['description'])

    def test_15_design_life_alone_means_neither_automatic_scrap_nor_extension(self):
        text = hazard(SCRAP)['conditions']
        self.assertIn('单纯达到设计使用年限不自动构成本项报废条件', text)
        self.assertIn('第一款报废条件以外且可以继续使用', text)
        self.assertIn('通过检验或者安全评估，并办理使用登记证书变更，方可继续使用', text)
        self.assertIn('加强检验、检测和维护保养', text)

    def test_16_scrapped_equipment_cannot_be_restored_by_evaluation_or_extension(self):
        self.assertIn('已报废设备不得以检验、安全评估或延长使用年限为由恢复使用',
                      hazard(SCRAP)['conditions'])
        self.assertIn('禁止使用国家明令淘汰和已经报废的特种设备',
                      FIXTURE['statutoryText']['TSELAW_32']['fullText'])
        self.assertIn('不得将已报废设备作为整改后可继续使用的设备验收', hazard(SCRAP)['measures'])


if __name__ == '__main__':
    unittest.main()
