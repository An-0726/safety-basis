"""Bounded regression checks for the 20-hazard remediation batch.

These exact-value checks prevent accidental polarity/scope drift. They do not
constitute professional verification of the rest of the corpus or site facts.
"""
from collections import Counter
from datetime import date
from commerce_cohort_fixture import pre_commerce_gate, pre_commerce_ids, pre_commerce_inventory, pre_commerce_manifest
import hashlib
import json
from pathlib import Path
import sys
import unittest
from power_fixture import CLAUSES as POWER_CLAUSES, EVIDENCE as POWER_EVIDENCE, VERSION as POWER_VERSION
from coal_fixture import CLAUSES as COAL_CLAUSES, EVIDENCE as COAL_EVIDENCE, VERSION as COAL_VERSION
from construction_fixture import CLAUSES as CONSTRUCTION_CLAUSES, EVIDENCE as CONSTRUCTION_EVIDENCE
from city_gas_fixture import CLAUSES as GAS_CLAUSES, EVIDENCE as GAS_EVIDENCE
from sector_directory_fixture import LAWS as SECTOR_LAWS, VERSIONS as SECTOR_VERSIONS, EVIDENCE as SECTOR_EVIDENCE

ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' /
                      'reviewed_remediation_20260930.json').read_text(encoding='utf-8'))
SCOPE_SUCCESSOR = json.loads((Path(__file__).parent / 'fixtures' /
                            'thirteen_scope_corrections_20260930.json').read_text(encoding='utf-8'))
SCOPE_ENTITIES = {row['path']: row for row in SCOPE_SUCCESSOR['entities']}


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def historical_entity(rel):
    """Keep this batch's original judgment, while guarding its exact successor."""
    if rel in SCOPE_ENTITIES:
        row = SCOPE_ENTITIES[rel]
        if read(rel) != row['record']:
            raise AssertionError('Source differs from its reviewed successor: ' + rel)
        return row['beforeRecord']
    return read(rel)


def hazard(hid):
    return read(f'knowledge/hazards/{hid}.json')


def link(kid):
    return read(f'knowledge/links/{kid}.json')


class DangerousDirectionRegressionTests(unittest.TestCase):
    """One separately reported regression for every corrected hazard."""


def direction_test(case):
    def test(self):
        actual = hazard(case['id'])
        self.assertEqual(actual['id'], case['id'])
        self.assertEqual(actual['lifecycle'], 'active')
        for field, value in case['changes'].items():
            self.assertEqual(actual[field], value, field)
        for phrase in case['requiredMeasurePhrases']:
            self.assertIn(phrase, actual['measures'])
    return test


for case in FIXTURE['hazards']:
    setattr(DangerousDirectionRegressionTests, 'test_direction_' + case['id'],
            direction_test(case))


class ReviewedRemediationBoundaryTests(unittest.TestCase):
    def test_exact_25_entities_and_canonical_id_lifecycle_inventory(self):
        self.assertEqual(len(FIXTURE['entities']), 25)
        for row in FIXTURE['entities']:
            with self.subTest(path=row['path']):
                self.assertEqual(content_hash(historical_entity(row['path'])), row['contentHash'])
        for kind, expected in FIXTURE['canonicalInventory'].items():
            rows = sorted((obj['id'], obj.get('lifecycle'))
                          for file in (KNOW / kind).glob('*.json')
                          for obj in [json.loads(file.read_text(encoding='utf-8'))])
            rows = pre_commerce_inventory(kind, rows)
            # Preserve this historical inventory verbatim after excluding only
            # the separately reviewed, semantically distinct GB12801 successor.
            successor = {'hazards': 'H_GB12801_2025_5_6_2_S1',
                         'links': 'K_GB12801_2025_5_6_2_S1'}.get(kind)
            if successor:
                self.assertEqual([row for row in rows if row[0] == successor],
                                 [(successor, 'active')])
                rows = [row for row in rows if row[0] != successor]
            # Exclude only the independently reviewed AQ3067 metadata identities;
            # they add no clauses, hazards, links or succession decisions.
            metadata_id = {'laws': 'LF_AQ3067',
                           'law-versions': 'LV_AQ3067_2026'}.get(kind)
            if metadata_id:
                self.assertEqual([row for row in rows if row[0] == metadata_id],
                                 [(metadata_id, 'active' if kind == 'laws' else None)])
                rows = [row for row in rows if row[0] != metadata_id]
            sector_ids = {'laws': SECTOR_LAWS, 'law-versions': SECTOR_VERSIONS}.get(kind, frozenset())
            self.assertEqual({row for row in rows if row[0] in sector_ids},
                             {(ident, 'active' if kind == 'laws' else None) for ident in sector_ids})
            rows = [row for row in rows if row[0] not in sector_ids]
            gas_ids = GAS_CLAUSES | CONSTRUCTION_CLAUSES | COAL_CLAUSES | POWER_CLAUSES if kind == 'clauses' else frozenset()
            self.assertEqual({row for row in rows if row[0] in gas_ids}, {(ident, 'active') for ident in gas_ids})
            rows = [row for row in rows if row[0] not in gas_ids]
            self.assertEqual(len(rows), expected['count'])
            digest = hashlib.sha256(json.dumps(rows, ensure_ascii=False,
                                              separators=(',', ':')).encode()).hexdigest()
            self.assertEqual(digest, expected['sha256'], kind)

    def test_43_substantive_reviews_have_exact_entity_and_context_bindings(self):
        self.assertEqual(len(FIXTURE['reviews']), 43)
        counts = Counter()
        for row in FIXTURE['reviews']:
            with self.subTest(path=row['path']):
                current_review = read(row['path'])
                entity_path = row['path'].replace('/reviews', '')
                # A later exact-scope review preserves the prior full record.
                # Do not rewrite this historical batch's reason or claim it
                # originally approved the successor scope.
                review = (current_review['previousReview'] if entity_path in SCOPE_ENTITIES
                          else current_review)
                entity = historical_entity(entity_path)
                counts[row['entityType']] += 1
                self.assertEqual(review['entityId'], row['entityId'])
                self.assertEqual(review['entityType'], row['entityType'])
                self.assertEqual(review['decision'], 'verified')
                self.assertEqual(review['checkedAt'], '2026-09-30')
                self.assertEqual(review['reviewer'], row.get('reviewer', 'Codex逐项内容复核20260930'))
                self.assertEqual(review['reason'], row['semanticReviewReason'])
                self.assertEqual(review['reviewedContentHash'], row['reviewedContentHash'])
                self.assertEqual(review['reviewedContentHash'], content_hash(entity))
                self.assertEqual(review.get('contextHashes'), row['contextHashes'])
                self.assertTrue(set(row['evidenceRefs']) <= set(review['evidenceRefs']))
                if 'exactEvidenceRefs' in row:
                    self.assertEqual(review['evidenceRefs'], row['exactEvidenceRefs'])
                self.assertIn('本次审核限', review['notes'])
                if row['entityType'] == 'link':
                    self.assertEqual(review['contextHashes']['hazard'], content_hash(historical_entity(f"knowledge/hazards/{entity['hazardId']}.json")))
                    self.assertEqual(review['contextHashes']['clause'], content_hash(historical_entity(f"knowledge/clauses/{entity['clauseId']}.json")))
                    if 'link' in review['contextHashes']:
                        self.assertEqual(review['contextHashes']['link'], content_hash(entity))
        self.assertEqual(counts, {'hazard': 20, 'link': 22, 'clause': 1})

    def test_29_unchanged_clause_and_version_reviews_remain_byte_identical(self):
        self.assertEqual(len(FIXTURE['preservedReviewFiles']), 29)
        for path, digest in FIXTURE['preservedReviewFiles'].items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)

    def test_nine_scoped_evidence_records_are_public_and_have_honest_hash_scope(self):
        self.assertEqual(len(FIXTURE['evidence']), 9)
        for row in FIXTURE['evidence']:
            with self.subTest(evidence=row['id']):
                obj = read(f"knowledge/evidence/{row['id']}.json")
                self.assertEqual(obj['id'], row['id'])
                self.assertEqual(obj['snapshotSha256'], row['snapshotSha256'])
                self.assertEqual(obj['url'], row['url'])
                self.assertEqual(obj['tier'], 'authoritative-public')
                self.assertTrue(obj['retrievedAt'].startswith('2026-09-30'))
                self.assertIn('规范化条款摘录', obj['notes'])
                self.assertIn('不是完整网页/PDF文件哈希', obj['notes'])
                self.assertTrue(obj['locator'])
                self.assertEqual(set(obj), {'id', 'url', 'tier', 'locator', 'page',
                                           'retrievedAt', 'snapshotSha256', 'notes'})
                serialized = json.dumps(obj, ensure_ascii=False)
                for forbidden in ('file://', '/workspace/', '/Users/', '/home/',
                                  'snapshotLocalPath', 'originalSourceFileSha256',
                                  'backend-audit', 'web工具', '云浏览器', '用户电脑'):
                    self.assertNotIn(forbidden, serialized)

    def test_manifest_counts_and_bounded_batch_totals(self):
        manifest = pre_commerce_manifest(read('knowledge/manifest.json'))
        self.assertEqual(manifest['batch'], 'civil-fireworks-reference-reading-20261001')
        self.assertEqual(sum(b['id'] == 'noncoal-reference-reading-20261001' for b in manifest['batches']), 1)
        self.assertEqual(sum(b['id'] == 'power-full-criteria-20261001' for b in manifest['batches']), 1)
        self.assertEqual(sum(b['id'] == 'coal-full-criteria-20261001' for b in manifest['batches']), 1)
        self.assertEqual(sum(b['id'] == 'construction-full-criteria-20261001' for b in manifest['batches']), 1)
        self.assertEqual(sum(b['id'] == 'city-gas-full-criteria-20261001' for b in manifest['batches']), 1)
        self.assertEqual(sum(b['id'] == 'sector-major-directory-metadata-20261001' for b in manifest['batches']), 1)
        self.assertEqual(sum(b['id'] == 'aq3067-metadata-reference-only-20261001' for b in manifest['batches']), 1)
        self.assertTrue(any(b['id'] == 'gb12801-first-sentence-transition-20261001'
                            for b in manifest['batches']))
        # The historical batch remains intact; its later scope successor adds
        # exactly fourteen separately traced source-specific evidence records.
        self.assertEqual(len(SCOPE_SUCCESSOR['evidence']), 14)
        # The later GB12801 slice adds two original-PDF records; the
        # historical batch entry below remains exactly as originally reviewed.
        # AQ3067 contributes only one further, explicitly identified metadata PDF record.
        expected_evidence = 1248 + len(SCOPE_SUCCESSOR['evidence']) + 2 + 1 + len(SECTOR_EVIDENCE) + len(GAS_EVIDENCE) + len(CONSTRUCTION_EVIDENCE) + len(COAL_EVIDENCE) + len(POWER_EVIDENCE)
        self.assertTrue((KNOW / 'evidence/E_AQ3067_2026_MEM_PDF.json').is_file())
        self.assertEqual(manifest['counts']['evidence'], expected_evidence)
        self.assertEqual(manifest['evidence'], expected_evidence)
        self.assertEqual(len(pre_commerce_ids('evidence', (p.stem for p in (KNOW / 'evidence').glob('*.json')))), expected_evidence)
        batch = next(b for b in manifest['batches'] if b['id'] == FIXTURE['batch'])
        self.assertEqual({k: batch[k] for k in ('evidenceAdded', 'hazardsCorrected',
            'linkScopesCorrected', 'clauseTextsCorrected', 'hazardReviewsUpdated',
            'linkReviewsUpdated', 'clauseReviewsUpdated')}, {
            'evidenceAdded': 9, 'hazardsCorrected': 20, 'linkScopesCorrected': 4,
            'clauseTextsCorrected': 1, 'hazardReviewsUpdated': 20,
            'linkReviewsUpdated': 22, 'clauseReviewsUpdated': 1})
        self.assertEqual(manifest['lifecycle'], {'active': 1664, 'proposed': 354, 'superseded': 113})

    def test_gb45067_scope_and_stop_repair_reinspection_restart_order(self):
        cases = [
            ('H_03466ADE0A589C7D890736A6', 'K_GB45067_03466ADE0A58_10', 'K_b064b1dc6d92606d0199f232', '不合格'),
            ('H_BD32095BBE999606E80E376E', 'K_GB45067_BD32095BBE99_3', 'K_affa50e64ea799b3c1ed437b', '不符合要求'),
        ]
        for hid, direct, supporting, conclusion in cases:
            with self.subTest(hazard=hid):
                h = hazard(hid)
                text = h['measures']
                self.assertIn(f'定期检验结论为“{conclusion}”', text)
                self.assertLess(text.index('立即停止使用'), text.index('完成修理整改'))
                self.assertLess(text.index('完成修理整改'), text.index('依法检验合格'))
                self.assertLess(text.index('依法检验合格'), text.index('后方可恢复使用'))
                self.assertEqual(link(direct)['applicability'], h['conditions'])
                self.assertEqual(link(direct)['role'], 'direct')
                self.assertEqual(link(supporting)['role'], 'supporting')
                for exclusion in ('军事装备', '核设施', '航空航天器', '铁路机车',
                                  '海上设施和船舶', '矿山井下', '民用机场专用设备', '不需要办理使用登记'):
                    self.assertIn(exclusion, h['conditions'])
        # Construction-site exclusion is vehicle/crane-specific, not all vessels.
        self.assertIn('房屋建筑工地、市政工程工地', hazard(cases[0][0])['conditions'])
        self.assertNotIn('房屋建筑工地', hazard(cases[1][0])['conditions'])
        version = read('knowledge/law-versions/LV_STD_E7182E7A85BA6017C48B96A8.json')
        self.assertEqual(version['effectiveDate'], '2024-12-01')

    def test_dust_duct_scope_does_not_leave_a_compliant_dry_tunnel_exception(self):
        h = hazard('H_15577_8_3_2_1')
        self.assertEqual(h['category'], '粉尘防爆')
        self.assertEqual(h['places'], ['粉尘爆炸危险场所的除尘系统风管'])
        self.assertEqual(h['conditions'], link('K_XLSX_0dac466595d5a96b9c29c60f')['applicability'])
        self.assertIn('普通通风管道不直接适用', h['conditions'])
        self.assertIn('煤矿井下、烟花爆竹、火炸药和强氧化剂', h['conditions'])
        self.assertNotIn('不符合要求的干式巷道', h['measures'])
        self.assertIn('停止使用现有干式巷道式构筑物除尘风道', h['measures'])

    def test_metal_positive_pressure_and_other_dust_are_distinct_branches(self):
        h = hazard('H_96106D7519F84C2DA149BB5819')
        k = link('K_PHASE6_D70AE69B0526086816016507')
        self.assertIn('金属粉尘除尘系统停止采用正压除尘方式', h['measures'])
        self.assertIn('其他可燃性粉尘受工艺条件限制', h['measures'])
        self.assertIn('不得用加装火花探测消除装置代替', h['measures'])
        self.assertIn('两个独立分支', k['reason'])
        self.assertIn('其他可燃性粉尘', k['applicability'])

    def test_article48_second_paragraph_has_one_consumer_and_no_scrapped_exception(self):
        cid = 'C_XLSX_FT_B5EB332AAF1DF679189544DF'
        consumers = [obj for file in (KNOW / 'links').glob('*.json')
                     for obj in [json.loads(file.read_text(encoding='utf-8'))]
                     if obj.get('clauseId') == cid]
        self.assertEqual([k['id'] for k in consumers], ['K_XLSX_FT_018BCD0DF4CAB382456C13D8'])
        c = read(f'knowledge/clauses/{cid}.json')
        self.assertEqual(c['articlePath'], '第四十八条第二款')
        self.assertTrue(c['quote'].startswith('前款规定报废条件以外'))
        self.assertIn('达到设计使用年限可以继续使用的', c['quote'])
        self.assertIn('办理使用登记证书变更，方可继续使用', c['quote'])
        self.assertIn('加强检验、检测和维护保养', c['quote'])
        h = hazard('H_8300469D69145B0731074A2CC4_2')
        self.assertIn('未被国家明令淘汰、未已经报废', h['measures'])
        self.assertNotIn('拟继续使用', h['measures'])
        self.assertIn('不得将已报废设备作为延长使用年限的对象', h['measures'])

    def test_occupational_unit_scope_and_fire_jurisdiction_object_boundaries(self):
        h = hazard('H_ZJWS_12_2')
        self.assertTrue(h['measures'].startswith('产生职业病危害的用人单位'))
        self.assertNotIn('仅', h['measures'])
        self.assertNotIn('不相容物质', h['description'])
        rail = hazard('H_JSXF_51_2')
        self.assertIn('江苏省行政区域', rail['conditions'])
        self.assertIn('运营设施和广告设施采用不燃、难燃材料', rail['measures'])
        self.assertIn('站台层、站厅付费区、乘客疏散区以及疏散通道', rail['measures'])
        for hid in ('H_216AA081EA9265D4DC2808F9D4_3', 'H_644EEE5EC12221D39672FE26E2_4'):
            self.assertIn('南京市行政区域', hazard(hid)['conditions'])
        self.assertIn('设置消防控制室的单位', hazard('H_216AA081EA9265D4DC2808F9D4_3')['description'])
        self.assertIn('歌舞娱乐放映游艺场所包厢、包间内', hazard('H_644EEE5EC12221D39672FE26E2_4')['measures'])

    def test_dated_gate_keeps_exact_batch_and_preserves_existing_containment(self):
        gate = evaluate_release_gate(KNOW, date(2026, 9, 30))
        for h in FIXTURE['hazards']:
            self.assertIn(h['id'], gate.eligible_hazards)
        for r in FIXTURE['reviews']:
            if r['entityType'] == 'link':
                self.assertIn(r['entityId'], gate.eligible_links)
        # Current projection additionally excludes the four independently reviewed
        # MEM10 wrong-source chains. The new containment suite reconstructs the
        # unchanged historical 1657/1791/1340 snapshot from preserved reviews.
        self.assertEqual(len(pre_commerce_gate(gate).eligible_hazards), 1653)
        self.assertEqual(len(pre_commerce_gate(gate).eligible_links), 1787)
        self.assertEqual(len({gate.links[k]['clauseId'] for k in pre_commerce_gate(gate).eligible_links}), 1338)
        self.assertNotIn('H_12158_10_1_2', gate.eligible_hazards)


if __name__ == '__main__':
    unittest.main()
