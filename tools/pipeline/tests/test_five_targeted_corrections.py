"""Exact text, scope and provenance checks for five bounded corrections.

These regressions guard the reviewed knowledge records and their publication
bindings. They are not a field adjudication engine or a whole-corpus legal audit.
"""
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' /
                      'five_targeted_corrections_20260930.json').read_text(encoding='utf-8'))
DUST = 'H_46A01ECE8B9C4AD0A9D66A841C'
CHARGING = 'H_A35BD266ADB24DF2A32373976A'
SCHOOL = 'H_JSXF_58_1'
KEY_UNIT = 'H_JSXF_58_2'
RESIDENT = 'H_JSXF_53_3'
SCHOOL_LINK = 'K_XLSX_FT_4996B3C832602A8FE3E7F750'
KEY_UNIT_LINK = 'K_XLSX_FT_1412F9552C73E6C403C39E08'


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def entity(kind, entity_id):
    return read(f'knowledge/{kind}/{entity_id}.json')


def quote(key):
    return FIXTURE['clauses'][key]['fullClauseQuote']


class FiveTargetedCorrectionTests(unittest.TestCase):
    def test_twelve_exact_approved_entities_and_stable_inventory(self):
        self.assertEqual(len(FIXTURE['entities']), 12)
        counts = Counter()
        for expected in FIXTURE['entities']:
            with self.subTest(path=expected['path']):
                counts[expected['path'].split('/')[1]] += 1
                self.assertEqual(content_hash(read(expected['path'])), expected['contentHash'])
                self.assertEqual(hashlib.sha256((ROOT / expected['path']).read_bytes()).hexdigest(),
                                 expected['fileSha256'])
        self.assertEqual(counts, {'hazards': 5, 'links': 6, 'clauses': 1})
        for kind, expected in FIXTURE['canonicalInventory'].items():
            rows = sorted((obj['id'], obj.get('lifecycle'))
                          for file in (KNOW / kind).glob('*.json')
                          for obj in [json.loads(file.read_text(encoding='utf-8'))])
            self.assertEqual(len(rows), expected['count'])
            self.assertEqual(hashlib.sha256(json.dumps(rows, ensure_ascii=False,
                separators=(',', ':')).encode()).hexdigest(), expected['sha256'])

    def test_twelve_individual_reviews_bind_exact_reasons_and_new_hashes(self):
        self.assertEqual(len(FIXTURE['reviews']), 12)
        counts = Counter()
        reasons = set()
        for expected in FIXTURE['reviews']:
            with self.subTest(path=expected['path']):
                review = read(expected['path'])
                obj = read(expected['path'].replace('/reviews', ''))
                self.assertEqual(review, expected['record'])
                self.assertEqual(hashlib.sha256((ROOT / expected['path']).read_bytes()).hexdigest(),
                                 expected['fileSha256'])
                self.assertEqual(review['reviewedContentHash'], content_hash(obj))
                self.assertEqual(review['decision'], 'verified')
                counts[review['entityType']] += 1
                reasons.add(review['reason'])
                if review['entityType'] == 'link':
                    self.assertEqual(review['contextHashes'], {
                        'hazard': content_hash(entity('hazards', obj['hazardId'])),
                        'clause': content_hash(entity('clauses', obj['clauseId']))})
        self.assertEqual(counts, {'hazard': 5, 'link': 6, 'clause': 1})
        self.assertEqual(len(reasons), 9, 'Preserve the exact individually approved review reasons')

    def test_four_evidence_snapshots_have_exact_bytes_and_source_urls(self):
        self.assertEqual(len(FIXTURE['evidence']), 4)
        for expected in FIXTURE['evidence']:
            with self.subTest(evidence=expected['id']):
                evidence = entity('evidence', expected['id'])
                self.assertEqual(evidence, expected['record'])
                self.assertEqual(hashlib.sha256(expected['snapshotText'].encode()).hexdigest(),
                                 evidence['snapshotSha256'])
                self.assertEqual(evidence['snapshotSha256'], expected['snapshotTextSha256'])
                self.assertEqual(hashlib.sha256((KNOW / 'evidence' /
                    (expected['id'] + '.json')).read_bytes()).hexdigest(), expected['fileSha256'])
                source = FIXTURE['sources'][expected['sourceId']]
                self.assertEqual(evidence['url'], source.get('fulltextUrl', source.get('officialFulltextUrl')))
                self.assertEqual(evidence['tier'], 'authoritative-public')
                self.assertIn('不是源PDF/HTML文件哈希', evidence['notes'])
                self.assertTrue(evidence['locator'])
        for clause in FIXTURE['clauses'].values():
            self.assertEqual(hashlib.sha256(clause['fullClauseQuote'].encode()).hexdigest(),
                             clause['quoteSha256'])

    def test_dust_text_requires_strictly_less_than_100_not_less_or_equal(self):
        h = entity('hazards', DUST)
        original = quote('gb15577_8_1_5')
        self.assertIn('接地电阻应小于100Ω', original)
        self.assertIn('接地电阻不小于100Ω', h['description'])
        self.assertIn('使接地电阻小于100Ω', h['measures'])
        for wrong in ('100Ω及以下', '100Ω 及以下', '不大于100Ω', '不大于 100Ω', '≤100Ω'):
            self.assertNotIn(wrong, h['measures'] + h['description'])
        # Boundary examples derive from the actual strict inequality in the text;
        # they do not purport to evaluate an entire on-site dust hazard.
        limit = float(re.search(r'使接地电阻小于(\d+)Ω', h['measures']).group(1))
        for resistance, meets_resistance_requirement in ((99.9, True), (100, False), (100.1, False)):
            with self.subTest(ohms=resistance):
                self.assertEqual(resistance < limit, meets_resistance_requirement)

    def test_dust_parallel_defects_flange_and_exclusions_are_preserved(self):
        h = entity('hazards', DUST)
        self.assertIn('未进行等电位连接、未可靠接地或接地电阻不小于100Ω', h['description'])
        self.assertIn('管道连接法兰采用跨接线', h['measures'])
        self.assertIn('粉尘爆炸危险场所除尘系统导电部件', h['conditions'])
        for exclusion in ('煤矿井下', '烟花爆竹', '火炸药', '强氧化剂'):
            self.assertIn(exclusion, h['conditions'])
        k = entity('links', 'K_XLSX_WEB_' + DUST)
        self.assertEqual(k['clauseId'], 'C_15577_8_1_5')
        self.assertEqual(k['role'], 'direct')
        self.assertNotIn('GB12158', k['applicability'])

    def test_charging_a_b_c_are_separate_and_only_c_requires_continued_use(self):
        h = entity('hazards', CHARGING)
        branches = h['description'].split('：', 1)[1].rstrip('。').split('；')
        self.assertEqual(branches, ['未经许可擅自从事充装活动', '移动式压力容器、气瓶错装介质',
                                  '充装设备设施上的紧急切断装置缺失或失效且仍继续使用'])
        self.assertNotIn('仍继续使用', branches[0])
        self.assertNotIn('仍继续使用', branches[1])
        self.assertIn('缺失或失效且仍继续使用', branches[2])
        source = quote('gb45067_4_5')
        a = source.split('a)', 1)[1].split('b)', 1)[0]
        b = source.split('b)', 1)[1].split('c)', 1)[0]
        c = source.split('c)', 1)[1]
        self.assertNotIn('仍继续使用', a + b)
        self.assertIn('缺失或失效，仍继续使用', c)
        k = entity('links', 'K_GB45067_A35BD266ADB2_5')
        self.assertIn('仅c项有仍继续使用限定', k['reason'])
        self.assertIn('不得将该限定加到a/b项', k['reason'])
        self.assertIn('不得将所有充装违规情形一律按本条判为重大事故隐患', h['measures'])

    def test_charging_subject_supervision_and_technical_roles_remain_distinct(self):
        h = entity('hazards', CHARGING)
        k = entity('links', 'K_GB45067_A35BD266ADB2_5')
        self.assertEqual(h['conditions'], k['applicability'])
        for text in (h['conditions'], k['applicability']):
            self.assertIn('主体责任为特种设备使用单位', text)
            self.assertIn('监督管理部门监督检查判定在本条中仅限4.5a)', text)
            self.assertIn('检验机构或技术机构提供技术支持', text)
            self.assertIn('不把4.5b)、4.5c)写成', text)
        self.assertIn('主体责任为特种设备使用单位', quote('gb45067_intro'))
        supporting = entity('links', 'K_43ef04628e3d0e5f615decbe')
        self.assertNotIn('监督检查判定', supporting['applicability'])

    def test_charging_scope_exclusions_do_not_exclude_all_construction_vessels(self):
        text = entity('hazards', CHARGING)['conditions']
        for phrase in ('军事装备', '核设施', '航空航天器', '铁路机车', '海上设施和船舶',
                       '矿山井下', '民用机场专用设备', '不需要办理使用登记'):
            self.assertIn(phrase, text)
        self.assertIn('排除项仅为起重机械和场（厂）内专用机动车辆', text)
        self.assertIn('不扩大为所有工地压力容器', text)
        self.assertIn('其他违规情形应另据适用条款', text)

    def test_charging_supporting_article49_has_separate_evidence_from_direct_standard(self):
        k = entity('links', 'K_43ef04628e3d0e5f615decbe')
        self.assertEqual(k['clauseId'], 'C_7D2425A6472F9ED7098B49315B')
        self.assertEqual(k['role'], 'supporting')
        self.assertIn('第四十九条', k['reason'])
        self.assertIn('不将所有充装违规一律认定', k['reason'])
        self.assertNotIn('第四十条', k['reason'])
        review = entity('reviews/links', k['id'])
        self.assertEqual(review['evidenceRefs'], ['E_BOUNDARY_20260930_TSELAW'])
        direct = entity('reviews/links', 'K_GB45067_A35BD266ADB2_5')
        self.assertEqual(direct['evidenceRefs'], ['E_BOUNDARY_20260930_GB45067'])
        self.assertIn('禁止对不符合安全技术规范要求', quote('tse49'))

    def test_school_title_and_description_cover_either_missing_activity(self):
        h = entity('hazards', SCHOOL)
        self.assertEqual(h['title'], '学校或其他教育机构未定期组织消防科普参观或应急疏散演练')
        self.assertIn('未定期组织师生参观消防科普教育场馆，或未定期开展应急疏散演练', h['description'])
        self.assertIn('分别核对参观和演练', h['measures'])
        self.assertIn('未规定具体次数或周期', h['conditions'])
        self.assertIn('不得把第二款重点单位的“每半年至少一次”自动套用给所有学校', h['conditions'])
        self.assertIn('未规定统一考核合格或岗位准入条件', h['measures'])

    def test_key_unit_half_year_frequency_and_two_drill_contents_are_preserved(self):
        h = entity('hazards', KEY_UNIT)
        for field in ('title', 'description', 'measures'):
            self.assertIn('每半年至少组织开展一次灭火和应急疏散演练', h[field])
            self.assertNotIn('每年两次', h[field])
        self.assertIn('灭火、应急疏散两项内容', h['description'])
        self.assertIn('先确认其重点单位属性', h['conditions'])
        self.assertIn('符合消防安全重点单位界定标准的个体工商户', h['conditions'])
        self.assertIn('不得以普通单位或人员密集场所身份直接替代', h['conditions'])
        self.assertIn('一般防火巡查或仅培训不能替代', h['measures'])
        self.assertIn('每半年至少', quote('jsxf58'))

    def test_school_and_key_unit_link_to_article58_not_article91(self):
        for kid, paragraph in ((SCHOOL_LINK, '第一款'), (KEY_UNIT_LINK, '第二款')):
            with self.subTest(link=kid):
                k = entity('links', kid)
                self.assertEqual(k['clauseId'], 'C_JSXF_58')
                self.assertIn('第58条' + paragraph, k['reason'])
                self.assertEqual(k['jurisdictionCode'], 'CN-32')
        self.assertIn('报请本级人民政府依法决定', quote('jsxf91'))
        self.assertNotIn('演练', quote('jsxf91'))

    def test_shared_article58_jurisdiction_and_exact_two_incoming_links(self):
        clause = entity('clauses', 'C_JSXF_58')
        version = entity('law-versions', clause['lawVersionId'])
        self.assertEqual(clause['jurisdictionCode'], 'CN-32')
        self.assertEqual(version['scope'], 'CN-32')
        self.assertEqual(re.sub(r'\s', '', clause['quote']), re.sub(r'\s', '', quote('jsxf58')))
        incoming = sorted(obj['id'] for file in (KNOW / 'links').glob('*.json')
                          for obj in [json.loads(file.read_text(encoding='utf-8'))]
                          if obj.get('clauseId') == 'C_JSXF_58')
        self.assertEqual(incoming, sorted([SCHOOL_LINK, KEY_UNIT_LINK]))
        for kid in incoming:
            self.assertEqual(entity('reviews/links', kid)['contextHashes']['clause'], content_hash(clause))
        self.assertEqual(entity('reviews/clauses', 'C_JSXF_58')['reviewedContentHash'], content_hash(clause))

    def test_jiangsu_avoidance_actor_is_not_property_company_or_nanjing_prohibition(self):
        h = entity('hazards', RESIDENT)
        self.assertEqual(h['title'], '业主或物业使用人未避免电动自行车或其蓄电池进入住宅电梯或户内')
        self.assertIn('江苏省行政区域内住宅的业主和物业使用人', h['conditions'])
        self.assertIn('业主和物业使用人提高消防安全防范意识', h['measures'])
        self.assertIn('避免将其带入住宅电梯和户内', h['measures'])
        self.assertIn('不能由此认定物业服务企业负有劝阻义务', h['conditions'])
        self.assertIn('不得把物业服务企业的劝阻记录', h['measures'])
        self.assertIn('不把“避免”改写为省级统一禁止性规定', h['description'])
        self.assertIn('南京市第50条第二款另有“禁止进入”规定，适用范围限南京市', h['note'])
        self.assertIn('避免电动自行车或者其蓄电池进入住宅的电梯和户内', quote('jsxf53'))
        self.assertIn('禁止电动自行车或者其蓄电池进入住宅的电梯和户内', quote('njxf50'))
        self.assertIn('本市行政区域', quote('njxf2'))
        k = entity('links', 'K_XLSX_NEW14_A9E65CF2ADA49CC4F1A5B24C')
        self.assertEqual(k['jurisdictionCode'], 'CN-32')
        self.assertIn('不支持物业服务企业未劝阻、南京禁止条款或行政处罚结论', k['reason'])

    def test_all_six_basis_bindings_match_their_own_source_and_locator(self):
        source_evidence = {e['sourceId']: e['id'] for e in FIXTURE['evidence']}
        self.assertEqual(len(FIXTURE['bindings']), 6)
        for expected in FIXTURE['bindings']:
            with self.subTest(link=expected['linkId']):
                k = entity('links', expected['linkId'])
                c = entity('clauses', k['clauseId'])
                review = entity('reviews/links', k['id'])
                for field in ('hazardId', 'clauseId', 'role', 'jurisdictionCode'):
                    self.assertEqual(k[field], expected[field])
                self.assertEqual(c['lawVersionId'], expected['lawVersionId'])
                self.assertEqual(review['evidenceRefs'], expected['exactEvidenceRefs'])
                self.assertEqual(review['evidenceRefs'], [source_evidence[expected['sourceId']]])
                self.assertEqual(review['reviewedContentHash'], expected['reviewedContentHash'])
                self.assertEqual(review['contextHashes'], expected['contextHashes'])
                self.assertTrue(expected['exactLocator'])
        # The province links must never inherit the city comparison as evidence.
        for kid in (SCHOOL_LINK, KEY_UNIT_LINK, 'K_XLSX_NEW14_A9E65CF2ADA49CC4F1A5B24C'):
            self.assertEqual(entity('reviews/links', kid)['evidenceRefs'], ['E_FIRE_CORRECTION_JSXF_20260930'])

    def test_three_existing_field_profiles_and_reviews_are_byte_identical(self):
        paths = FIXTURE['preservedFieldProfileFiles']
        self.assertEqual(sum('/records/' in path for path in paths), 3)
        self.assertEqual(sum('/reviews/' in path for path in paths), 3)
        for path, expected_hash in paths.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), expected_hash)

    def test_manifest_only_gains_four_evidence_records(self):
        manifest = read('knowledge/manifest.json')
        self.assertEqual(manifest['counts']['evidence'], FIXTURE['totalEvidenceCount'])
        self.assertEqual(manifest['evidence'], FIXTURE['totalEvidenceCount'])
        self.assertEqual(len(list((KNOW / 'evidence').glob('*.json'))), FIXTURE['totalEvidenceCount'])
        self.assertEqual(manifest['lifecycle'], {'active': 1663, 'proposed': 354, 'superseded': 113})

    def test_dated_gate_admits_all_five_hazards_and_six_exact_links(self):
        gate = evaluate_release_gate(KNOW, date.fromisoformat(FIXTURE['asOf']))
        for hid in (DUST, CHARGING, SCHOOL, KEY_UNIT, RESIDENT):
            with self.subTest(hazard=hid):
                self.assertIn(hid, gate.eligible_hazards)
                self.assertEqual(gate.hazards[hid]['reasons'], [])
        for binding in FIXTURE['bindings']:
            kid = binding['linkId']
            with self.subTest(link=kid):
                self.assertIn(kid, gate.eligible_links)
                self.assertEqual(gate.links[kid]['reasons'], [])
                self.assertEqual(gate.links[kid]['qualifying'], binding['role'] == 'direct')


if __name__ == '__main__':
    unittest.main()
