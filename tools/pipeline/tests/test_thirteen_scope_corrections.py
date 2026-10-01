"""Exact scope, evidence, history and fail-closed regressions for thirteen repairs.

The source model is prose, not a field-fact or legal adjudication engine. These
checks bind the independently reviewed wording and its precise statutory branches;
they do not invent a second Boolean classifier and call it production coverage.
Negative gate tests copy real records into disposable directories, never renew a
production review, and never require the private audit inputs to exist in CI.
"""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from sector_directory_fixture import EVIDENCE as SECTOR_EVIDENCE
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from field_profiles import ProfileContext, digest, public_projection, review_bindings, validate_profile
from release_gate_core import evaluate_release_gate

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' /
                     'thirteen_scope_corrections_20260930.json').read_text(encoding='utf-8'))
AS_OF = date(2026, 9, 30)
TOOLS = 'H_15577_10_5_1'
MAINTENANCE = 'H_15577_10_7_1'
ELECTRICAL = 'H_15577_6_3_3_2'
ISOLATION = 'H_15577_7_1_3_1'
WET = 'H_15577_8_4_10_2'
MONITOR = 'H_216AA081EA9265D4DC2808F9D4_3'
RESCUE = 'H_48B66BAC_15_4'
ALARM = 'H_644EEE5EC12221D39672FE26E2_4'
EXTENSION = 'H_8300469D69145B0731074A2CC4_2'
RENTAL = 'H_A9E328C34EF033693BC2FEEF3F_1'
RESTART = 'H_FCB_19_4'
TRANSIT = 'H_JSXF_51_2'
HEALTH = 'H_ZJWS_12_2'
DUST = (TOOLS, MAINTENANCE, ELECTRICAL, ISOLATION, WET)
TARGETS = set(DUST) | {MONITOR, RESCUE, ALARM, EXTENSION, RENTAL, RESTART, TRANSIT, HEALTH}


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def hazard(ident):
    return read(f'knowledge/hazards/{ident}.json')


def source_text(ident):
    return FIXTURE['statutoryText'][ident]['text']


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(root, relative, obj):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')


def replay_guarded_patch(raw, row):
    """Replay the exact approved test/replace contract; do not write any source."""
    if sha(raw) != row['oldFileSha256']:
        raise ValueError('baseline_file_sha256')
    obj = json.loads(raw)
    if content_hash(obj) != row['oldContentHash']:
        raise ValueError('baseline_content_hash')
    for operation in row['operations']:
        field = operation['path'].removeprefix('/')
        if operation['op'] == 'test':
            if obj[field] != operation['value']:
                raise ValueError('baseline_field_value:' + field)
        elif operation['op'] == 'replace':
            obj[field] = operation['value']
        else:
            raise ValueError('unapproved_operation')
    return obj


class ThirteenScopeProvenanceTests(unittest.TestCase):
    def test_exact_26_entities_and_41_guarded_fields(self):
        self.assertEqual(FIXTURE['baselineCommit'], 'a35a5cf1a5c395f70df2db0f1e6a940d93a8fd70')
        self.assertEqual(FIXTURE['assessmentSha256'],
                         '5466d8fb742dc40091640de0029513a6c4cc7b072d685b0f64236707429bd947')
        self.assertEqual(len(FIXTURE['entities']), 26)
        self.assertEqual({r['hazardId'] for r in FIXTURE['entities']}, TARGETS)
        self.assertEqual(sum(len(r['modifiedFields']) for r in FIXTURE['entities']), 41)
        for row in FIXTURE['entities']:
            with self.subTest(path=row['path']):
                actual = read(row['path'])
                self.assertEqual(actual, row['record'])
                self.assertEqual(actual, replay_guarded_patch(row['beforeFileText'].encode(), row))
                self.assertEqual(sha((ROOT / row['path']).read_bytes()), row['fileSha256'])
                self.assertEqual(content_hash(actual), row['contentHash'])
                self.assertNotEqual(row['oldContentHash'], row['contentHash'])
                self.assertEqual({k: actual[k] for k in row['unchangedFields']}, row['unchangedFields'])
                self.assertNotIn('measures', row['modifiedFields'])
                expected = {'conditions', 'places'} if '/hazards/' in row['path'] else {'applicability'}
                if row['record']['id'] == WET:
                    expected |= {'title', 'description'}
                self.assertEqual(set(row['modifiedFields']), expected)

    def test_guarded_patch_replay_rejects_wrong_file_hash_or_old_value(self):
        for row in FIXTURE['entities']:
            with self.subTest(path=row['path']):
                raw = row['beforeFileText'].encode()
                with self.assertRaisesRegex(ValueError, 'baseline_file_sha256'):
                    replay_guarded_patch(raw + b' ', row)
                bad = copy.deepcopy(row)
                bad['oldContentHash'] = '0' * 64
                with self.assertRaisesRegex(ValueError, 'baseline_content_hash'):
                    replay_guarded_patch(raw, bad)
                bad = copy.deepcopy(row)
                bad['operations'][0]['value'] = 'unapproved old-value substitution'
                with self.assertRaisesRegex(ValueError, 'baseline_field_value'):
                    replay_guarded_patch(raw, bad)

    def test_each_direct_link_has_the_same_exact_scope_and_stable_source_identity(self):
        self.assertEqual(set(FIXTURE['sourceFamilies']), TARGETS)
        for hid, expected in FIXTURE['sourceFamilies'].items():
            with self.subTest(hazard=hid):
                link = read(f"knowledge/links/{expected['linkId']}.json")
                clause = read(f"knowledge/clauses/{expected['clauseId']}.json")
                version = read(f"knowledge/law-versions/{expected['lawVersionId']}.json")
                self.assertEqual(link['hazardId'], hid)
                self.assertEqual(link['role'], 'direct')
                self.assertEqual(link['clauseId'], expected['clauseId'])
                self.assertEqual(link['applicability'], hazard(hid)['conditions'])
                self.assertEqual(clause['lawVersionId'], expected['lawVersionId'])
                self.assertEqual(version['lawId'], expected['lawId'])
                actual_links = sorted(read(str(p.relative_to(ROOT)))['id']
                                      for p in (KNOW / 'links').glob('*.json')
                                      if read(str(p.relative_to(ROOT))).get('hazardId') == hid)
                self.assertEqual(actual_links, expected['associationIds'])

    def test_complete_old_review_history_is_preserved_and_hash_bound(self):
        self.assertEqual(len(FIXTURE['reviews']), 26)
        self.assertEqual(FIXTURE['individualSourceDecisionsSha256'],
                         '613f5b383f64e30e5dc0b5b8b6dba087bc03009d2636ad0363e6e9fa24178a5f')
        self.assertEqual(FIXTURE['captureState'], 'independently_reviewed_records_captured')
        for row in FIXTURE['reviews']:
            with self.subTest(path=row['path']):
                actual = read(row['path'])
                self.assertEqual(actual, row['record'])
                self.assertEqual(sha((ROOT / row['path']).read_bytes()), row['fileSha256'])
                self.assertEqual(actual['previousReview'], row['previousReview'])
                self.assertEqual(actual['historySha256'], digest(row['previousReview']))
                self.assertEqual(actual['historySha256'], row['previousReviewSha256'])
                self.assertEqual(actual['previousReviewFileSha256'], row['previousFileSha256'])
                self.assertNotEqual(actual['reason'], row['previousReview'].get('reason'))
                self.assertEqual(actual['decision'], 'verified')
                self.assertEqual(actual['reviewer'], 'Codex十三项源范围独立复核20260930')
                base_review = {k: v for k, v in actual.items() if k not in
                               ('previousReview', 'historySha256', 'previousReviewFileSha256', 'reviewEvidence')}
                self.assertEqual(digest(base_review), row['approvedReviewSha256'])
                self.assertEqual(actual['reviewEvidence']['individualSourceDecisionsSha256'],
                                 FIXTURE['individualSourceDecisionsSha256'])
                self.assertEqual(actual['reviewEvidence']['sourceScopeAssessmentSha256'],
                                 FIXTURE['assessmentSha256'])
                self.assertIs(actual['reviewEvidence']['profileAdmission'], False)
                self.assertIs(actual['reviewEvidence']['siteFactsVerified'], False)
                source_path = row['path'].replace('/reviews', '')
                source_row = next(r for r in FIXTURE['entities'] if r['path'] == source_path)
                reviewed_fields = {'/' + field for field in source_row['modifiedFields']}
                self.assertEqual(set(actual['reviewedFields']), reviewed_fields)
                self.assertEqual(set(actual['fieldEvidenceRefs']), reviewed_fields)
                self.assertEqual(actual['reviewedValues'],
                                 {'/' + field: source_row['record'][field]
                                  for field in source_row['modifiedFields']})
                for refs in actual['fieldEvidenceRefs'].values():
                    self.assertTrue(refs)
                    self.assertTrue(set(refs) <= set(actual['evidenceRefs']))
                self.assertEqual({ref for refs in actual['fieldEvidenceRefs'].values() for ref in refs},
                                 set(actual['evidenceRefs']))
                if actual['entityId'] == WET:
                    self.assertEqual(actual['fieldEvidenceRefs']['/title'],
                                     ['E_SCOPE_20260930_GB15577_8_4_10'])
                self.assertEqual(actual['reviewedContentHash'],
                                 content_hash(read(row['path'].replace('/reviews', ''))))
                if actual['entityType'] == 'link':
                    link = read(row['path'].replace('/reviews', ''))
                    self.assertEqual(actual['contextHashes'], {
                        'hazard': content_hash(hazard(link['hazardId'])),
                        'clause': content_hash(read(f"knowledge/clauses/{link['clauseId']}.json"))})

    def test_evidence_is_exact_and_source_specific_for_all_26_reviews(self):
        evidence = {row['id']: row for row in FIXTURE['evidence']}
        self.assertEqual(len(evidence), 14)
        for eid, row in evidence.items():
            with self.subTest(evidence=eid):
                actual = read(f'knowledge/evidence/{eid}.json')
                self.assertEqual(actual, row['record'])
                self.assertEqual(row['fileSha256'], row['independentlyFinalizedEvidenceFileSha256'])
                self.assertEqual(sha((KNOW / 'evidence' / (eid + '.json')).read_bytes()), row['fileSha256'])
                self.assertTrue(actual['locator'])
                self.assertTrue(actual['url'])
                self.assertEqual(actual['tier'], 'authoritative-public')
                if row['hashMeaning'] == 'normalized_official_excerpt':
                    normalized = '\n'.join(re.sub(r'\s+', '', part) for part in row['excerptParts'])
                    self.assertEqual(sha(normalized.encode()), actual['snapshotSha256'])
                    self.assertIn('不是完整网页/PDF文件哈希', actual['notes'])
                else:
                    self.assertEqual(row['hashMeaning'], 'verified_original_pdf_bytes')
                    self.assertEqual(actual['snapshotSha256'],
                                     '1cd35b2f56874673b41f99e82db10d0d973a7f8dbd1a9f1dade2008fbaa97c74')
                    self.assertIn('完整PDF文件SHA256', actual['notes'])
        for eid, binding in FIXTURE['evidenceSourceBindings'].items():
            obj = read(f'knowledge/evidence/{eid}.json')
            self.assertEqual(obj['url'], binding['url'])
            self.assertEqual(obj['locator'], binding['locator'])
            self.assertEqual(sha((KNOW / 'evidence' / (eid + '.json')).read_bytes()), binding['fileSha256'])
            self.assertTrue(binding['lawIds'])
        for row in FIXTURE['reviews']:
            with self.subTest(review=row['path']):
                review = read(row['path'])
                family = FIXTURE['sourceFamilies'][row['hazardId']]
                self.assertEqual(review['evidenceRefs'], row['exactEvidenceRefs'])
                self.assertEqual(sorted(review['evidenceRefs']), family['expectedEvidenceRefs'])
                self.assertEqual(len(review['evidenceRefs']), len(set(review['evidenceRefs'])))
                self.assertTrue(review['evidenceRefs'])
                for eid in review['evidenceRefs']:
                    self.assertIn(family['lawId'], FIXTURE['evidenceSourceBindings'][eid]['lawIds'],
                                  'A convenient unrelated standard cannot support this source')
                peer = read(f"knowledge/reviews/hazards/{row['hazardId']}.json")
                self.assertEqual(review['evidenceRefs'], peer['evidenceRefs'])

    def test_all_unchanged_associations_and_upstream_records_keep_original_bytes(self):
        self.assertEqual(len(FIXTURE['preservedAssociatedFiles']), 79)
        for path, expected in FIXTURE['preservedAssociatedFiles'].items():
            with self.subTest(path=path):
                self.assertEqual(sha((ROOT / path).read_bytes()), expected)

    def test_all_six_profiles_keep_original_bytes_and_complete_dependencies(self):
        self.assertEqual(len(FIXTURE['preservedProfiles']), 6)
        context = ProfileContext(KNOW)
        changed = {r['path'].removeprefix('knowledge/').removesuffix('.json')
                   for r in FIXTURE['entities'] + FIXTURE['reviews']}
        for row in FIXTURE['preservedProfiles']:
            with self.subTest(profile=row['id']):
                base = KNOW / 'field-profiles/v1'
                record_path = base / 'records' / (row['id'] + '.json')
                review_path = base / 'reviews' / (row['id'] + '.json')
                profile = json.loads(record_path.read_text(encoding='utf-8'))
                self.assertEqual(sha(record_path.read_bytes()), row['recordFileSha256'])
                self.assertEqual(sha(review_path.read_bytes()), row['reviewFileSha256'])
                dependencies = context.dependencies(profile)
                self.assertFalse(set(dependencies) & changed)
                self.assertEqual(dependencies['associationIds'], row['associationIds'])
                self.assertEqual(set(dependencies) - {'associationIds'},
                                 {p.removeprefix('knowledge/').removesuffix('.json')
                                  for p in row['dependencyFileSha256']})
                for path, expected in row['dependencyFileSha256'].items():
                    self.assertEqual(sha((ROOT / path).read_bytes()), expected, path)
                self.assertEqual(review_bindings(profile, context), row['binding'])
        public = public_projection(KNOW, as_of=AS_OF)['public']
        self.assertEqual(digest(public), FIXTURE['publicProfilesSha256'])
        self.assertEqual(sorted(p['id'] for p in public['records']), FIXTURE['publicProfileIds'])

    def test_scope_source_approval_never_invents_profile_or_observed_facts(self):
        profiles = public_projection(KNOW, as_of=AS_OF)['public']['records']
        self.assertFalse({p['hazardId'] for p in profiles} & TARGETS)
        for profile in profiles:
            self.assertIs(profile['observedViolation'], False)
            if profile.get('profileKind') == 'routing_only':
                self.assertIsNone(profile['findingTemplate'])
        for hid in TARGETS:
            record = hazard(hid)
            self.assertNotIn('observedViolation', record)
            self.assertNotIn('findingTemplate', record)
            self.assertNotIn('perUseFacts', record)

    def test_statutory_excerpt_integrity_and_fourteen_new_evidence_records(self):
        for row in FIXTURE['statutoryText'].values():
            self.assertEqual(sha(row['text'].encode()), row['sha256'])
        self.assertEqual(len(FIXTURE['newEvidenceIds']), 14)
        self.assertEqual(set(FIXTURE['newEvidenceIds']),
                         {e['id'] for e in FIXTURE['evidence'] if e['newInThisBatch']})
        manifest = read('knowledge/manifest.json')
        # Preserve the fourteen-record historical fixture; two later original-
        # PDF records belong to GB12801; the third exact ID is metadata-only AQ3067.
        later_ids = {'E_GB12801_EFFECTIVE_20261001', 'E_GB12801_SCOPE_5_6_2_20261001',
                     'E_AQ3067_2026_MEM_PDF'} | SECTOR_EVIDENCE
        evidence_ids = {p.stem for p in (KNOW / 'evidence').glob('*.json')}
        self.assertTrue(later_ids <= evidence_ids)
        self.assertEqual(len(evidence_ids - later_ids), 1262)
        self.assertEqual(manifest['counts']['evidence'], 1265 + len(SECTOR_EVIDENCE))
        self.assertEqual(manifest['evidence'], 1265 + len(SECTOR_EVIDENCE))
        self.assertEqual(len(evidence_ids), 1265 + len(SECTOR_EVIDENCE))


class ThirteenScopeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = ProfileContext(KNOW)

    def snapshot(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        for hid, family in FIXTURE['sourceFamilies'].items():
            deps = self.context.dependencies({'hazardId': hid, 'basisLinkIds': [family['linkId']]})
            for key, obj in deps.items():
                if key == 'associationIds':
                    continue
                self.assertIsNotNone(obj, key)
                write(root, key + '.json', obj)
        return root

    def test_accepted_sources_pass_the_dated_gate_without_profile_approval(self):
        gate = evaluate_release_gate(KNOW, AS_OF)
        self.assertTrue(TARGETS <= gate.eligible_hazards)
        self.assertTrue({r['linkId'] for r in FIXTURE['sourceFamilies'].values()} <= gate.eligible_links)
        self.assertNotIn('H_12158_10_1_2', gate.eligible_hazards)
        # Current projection additionally excludes the four independently reviewed
        # MEM10 wrong-source chains. The new containment suite reconstructs the
        # unchanged historical 1657/1791/1340 snapshot from preserved reviews.
        self.assertEqual(len(gate.eligible_hazards), 1653)
        self.assertEqual(len(gate.eligible_links), 1787)

    def test_changed_sources_cannot_reuse_any_old_content_or_context_review(self):
        root = self.snapshot()
        for row in FIXTURE['reviews']:
            write(root, row['path'].removeprefix('knowledge/'), row['previousReview'])
        gate = evaluate_release_gate(root, AS_OF)
        self.assertFalse(TARGETS & gate.eligible_hazards)
        for hid, family in FIXTURE['sourceFamilies'].items():
            with self.subTest(hazard=hid):
                self.assertIn('BLOCK_REVIEW_STALE', gate.hazards[hid]['reasons'])
                self.assertIn('BLOCK_REVIEW_STALE', gate.links[family['linkId']]['reasons'])
                self.assertIn('BLOCK_REVIEW_CONTEXT_STALE:hazard_context_stale',
                              gate.links[family['linkId']]['reasons'])
                self.assertNotIn(family['linkId'], gate.eligible_links)

    def test_content_hash_only_tampering_does_not_renew_old_link_context(self):
        root = self.snapshot()
        for row in FIXTURE['reviews']:
            if '/links/' not in row['path']:
                continue
            # Deliberate invalid-sidecar mutation, confined to a temporary tree.
            # No semantic decision or context approval is synthesized.
            invalid = copy.deepcopy(row['previousReview'])
            invalid['reviewedContentHash'] = content_hash(read(row['path'].replace('/reviews', '')))
            write(root, row['path'].removeprefix('knowledge/'), invalid)
        gate = evaluate_release_gate(root, AS_OF)
        for family in FIXTURE['sourceFamilies'].values():
            with self.subTest(link=family['linkId']):
                self.assertNotIn(family['linkId'], gate.eligible_links)
                self.assertIn('BLOCK_REVIEW_CONTEXT_STALE:hazard_context_stale',
                              gate.links[family['linkId']]['reasons'])

    def test_profile_level_success_cannot_bypass_stale_source_gate(self):
        root = self.snapshot()
        for row in FIXTURE['reviews']:
            write(root, row['path'].removeprefix('knowledge/'), row['previousReview'])
        template = read('knowledge/field-profiles/v1/records/FPR_ROUTING_JSXF_58_1.json')
        profile_ids = {}
        for hid, family in FIXTURE['sourceFamilies'].items():
            profile = copy.deepcopy(template)
            profile.update(id='FPR_TEST_SOURCE_GATE_' + hid, hazardId=hid,
                           basisLinkIds=[family['linkId']])
            self.assertEqual(validate_profile(profile), [])
            profile_ids[profile['id']] = family['linkId']
            write(root, 'field-profiles/v1/records/' + profile['id'] + '.json', profile)
        # Simulate successful profile-level checks without authoring a review.
        # Real source gate and projection code still run and must reject all 13.
        with patch('field_profiles._review_errors', return_value=[]) as profile_checks:
            result = public_projection(root, as_of=AS_OF)
        self.assertEqual(profile_checks.call_count, 13)
        self.assertFalse(result['public']['records'])
        excluded = {r['profileId']: r['reasons'] for r in result['inventory']['excludedProfiles']}
        self.assertEqual(set(excluded), set(profile_ids))
        for ident, link_id in profile_ids.items():
            self.assertIn('SOURCE_HAZARD_GATE_FAILED', excluded[ident])
            self.assertIn('SELECTED_BASIS_GATE_FAILED:' + link_id, excluded[ident])

    def test_removing_any_target_review_fails_closed(self):
        root = self.snapshot()
        for row in FIXTURE['reviews']:
            (root / row['path'].removeprefix('knowledge/')).unlink()
        gate = evaluate_release_gate(root, AS_OF)
        self.assertFalse(TARGETS & gate.eligible_hazards)
        for hid, family in FIXTURE['sourceFamilies'].items():
            self.assertIn('BLOCK_REVIEW_MISSING', gate.hazards[hid]['reasons'])
            self.assertIn('BLOCK_REVIEW_MISSING', gate.links[family['linkId']]['reasons'])


class ThirteenScopeSemanticBoundaryTests(unittest.TestCase):
    def test_all_five_dust_objects_keep_exact_four_exclusions(self):
        for hid in DUST:
            with self.subTest(hazard=hid):
                text = hazard(hid)['conditions']
                self.assertIn('GB 15577-2018范围内', text)
                self.assertIn('不适用于煤矿井下、烟花爆竹、火炸药和强氧化剂的粉尘场所', text)
                self.assertIn('不构成粉尘爆炸危险的普通粉尘场景不直接适用', text)
                self.assertNotIn('不适用于煤炭行业', text)
                self.assertNotIn('不适用于煤矿地面', text)

    def test_dust_internal_equipment_hazard_is_not_gated_by_room_air_explosion(self):
        terms = FIXTURE['dustScopeAndTerms']['verbatimTerms']
        self.assertEqual(terms['3.3 粉尘爆炸危险场所'], '存在可燃性粉尘和气态氧化剂（主要是空气）的场所。')
        self.assertIn('混合物被点燃后', terms['3.2 爆炸性粉尘环境'])
        for hid in DUST:
            text = hazard(hid)['conditions']
            for extra_prerequisite in ('设备外部已形成', '外部空气达到爆炸浓度', '仅室内空气', '已发生爆炸'):
                self.assertNotIn(extra_prerequisite, text)
        self.assertIn('存在粉尘爆炸危险的工艺设备', hazard(ISOLATION)['conditions'])
        self.assertIn('湿式除尘系统', hazard(WET)['conditions'])

    def test_tools_cover_preventive_selection_without_presuming_stored_iron_tool_use(self):
        text = hazard(TOOLS)['conditions']
        self.assertIn('检修作业及其检修作业工具', text)
        self.assertIn('防止产生火花的防爆工具', text)
        self.assertIn('禁止使用铁质检修作业工具', text)
        self.assertNotIn('实际使用的检修工具', text)
        self.assertNotIn('储存铁质工具即', text)
        self.assertIn('检修作业应采用', source_text(TOOLS))

    def test_maintenance_includes_facilities_and_collection_system_maintenance(self):
        text = hazard(MAINTENANCE)['conditions']
        self.assertIn('设备设施检修作业及相关检修维护', text)
        self.assertIn('按照设备检修维护规程和程序作业', text)
        self.assertIn('粉尘爆炸危险场所禁止交叉作业', text)
        self.assertIn('除尘系统、电气设备等进行检修维护',
                      FIXTURE['dustScopeAndTerms']['contextQuotes']['10.2'])
        self.assertNotIn('全部日常生产', text)

    def test_electrical_prevention_has_two_independent_duties_without_actual_ignition_gate(self):
        text = hazard(ELECTRICAL)['conditions']
        self.assertIn('粉尘爆炸危险场所用电气设备和线路', text)
        self.assertIn('防止由电气设备或线路产生的过热及火花', text)
        self.assertIn('以及防止可燃性粉尘进入产生电火花或高温部件的外壳内', text)
        for wrong in ('已经产生火花的设备', '已经进入粉尘时才', '全部普通线路'):
            self.assertNotIn(wrong, text)
        self.assertIn('；应防止', source_text(ELECTRICAL))

    def test_process_control_rejects_isolation_alone_without_requiring_all_controls(self):
        text = hazard(ISOLATION)['conditions']
        self.assertIn('存在粉尘爆炸危险的工艺设备', text)
        self.assertIn('采用适用控爆措施且不能单独采取隔爆', text)
        self.assertIn('一种或多种控爆方式，但不能单独采取隔爆', source_text(ISOLATION))
        for wrong in ('全部四种', '四种同时', '只要隔爆即可'):
            self.assertNotIn(wrong, text)

    def test_wet_system_is_not_dry_system_and_mud_or_ventilation_defect_is_sufficient(self):
        h = hazard(WET)
        self.assertIn('湿式除尘系统', h['conditions'])
        self.assertEqual(h['places'], ['粉尘爆炸危险场所的湿式除尘系统'])
        self.assertIn('未及时清除沉淀泥浆，或者', h['description'])
        self.assertIn('水槽（箱）、水质过滤池（箱）', h['description'])
        self.assertIn('开启或停止状态下未保持良好通风', h['description'])
        self.assertIn('在开机和停机状态下的良好通风', h['conditions'])
        self.assertIn('无论除尘器处于开启或者停止状态，都要有良好的通风', source_text(WET))
        self.assertNotIn('未清泥浆且通风不良', h['description'])

    def test_nanjing_special_domains_are_conditional_overrides_not_absolute_exclusions(self):
        for hid in (MONITOR, ALARM):
            with self.subTest(hazard=hid):
                text = hazard(hid)['conditions']
                self.assertIn('南京市行政区域内', text)
                self.assertIn('法律、法规对森林、铁路、港口（含渔业港口）、民航', text)
                self.assertIn('在内河水域内航行、停泊、作业的民用船舶以及相关设施', text)
                self.assertIn('消防工作另有规定的，从其规定', text)
                self.assertNotIn('不适用于森林、铁路', text)
                self.assertNotIn('全省行政区域', text)

    def test_remote_monitoring_requires_control_room_and_each_operational_branch(self):
        text = hazard(MONITOR)['conditions']
        self.assertIn('设置消防控制室的单位', text)
        self.assertIn('接入城市消防远程监控中心监测系统并实时传输', text)
        self.assertIn('联网设施和传输网络正常使用、不得擅自拆除或停用', text)
        self.assertIn('监测信息采集不替代单位消防安全主体责任', text)
        self.assertNotIn('所有消防安全重点单位', text)
        self.assertNotIn('未接入且未传输且停用', text)
        self.assertIn('设置消防控制室的单位应当', source_text(MONITOR))

    def test_alarm_covers_only_listed_private_rooms_and_sound_or_video(self):
        text = hazard(ALARM)['conditions']
        self.assertIn('歌舞娱乐放映游艺场所的包厢、包间', text)
        self.assertIn('同步声音或者视像警报', text)
        self.assertIn('火灾发生初期消除原有画面音响、播送火灾警报的功能', text)
        self.assertIn('不扩展为所有房间或所有公共娱乐场所空间', text)
        self.assertNotIn('声音和视像警报同时', text)
        self.assertNotIn('已发生真实火灾后才', text)
        self.assertIn('应当同步设置声音或者视像警报', source_text(ALARM))

    def test_extension_keeps_objective_eligibility_separate_from_unmet_compliance(self):
        text = hazard(EXTENSION)['conditions']
        self.assertIn('不属于特种设备安全法第四十八条第一款报废条件', text)
        self.assertIn('未被国家明令淘汰且未已经报废', text)
        self.assertIn('达到设计使用年限并按安全技术规范可以继续使用', text)
        self.assertIn('是否已通过检验或者安全评估、是否已办理使用登记证书变更属于本项核查内容', text)
        self.assertIn('不作为进入核查范围的前提', text)
        self.assertIn('未履行前述义务而继续使用的情形不得漏查', text)
        self.assertNotIn('已检验合格且已变更登记的特种设备', hazard(EXTENSION)['places'][0])

    def test_extension_inspection_or_assessment_still_requires_registration_and_aftercare(self):
        text = hazard(EXTENSION)['conditions']
        self.assertIn('须按规范通过检验或者安全评估并办理使用登记证书变更', text)
        self.assertIn('允许继续使用后应加强检验、检测和维护保养', text)
        self.assertNotIn('检验和安全评估均通过', text)
        self.assertIn('按照安全技术规范的要求通过检验或者安全评估，并办理使用登记证书变更',
                      source_text('TSE_48'))
        self.assertIn('禁止使用国家明令淘汰和已经报废的特种设备', source_text('TSE_32'))

    def test_rental_requires_actual_rental_and_keeps_all_six_independent_prohibitions(self):
        text = hazard(RENTAL)['conditions']
        self.assertIn('仅适用于特种设备出租单位及其实际出租活动', text)
        branches = ('未取得许可生产', '国家明令淘汰', '已经报废',
                    '未按安全技术规范维护保养', '未经检验', '检验不合格')
        for branch in branches:
            with self.subTest(independent_prohibition=branch):
                self.assertIn(branch, text)
        self.assertIn('应逐项核对实际涉及的禁止分支', text)
        self.assertNotIn('六项同时', text)
        self.assertNotIn('仅自用即属于出租', text)
        self.assertIn('特种设备出租单位不得出租', source_text('TSE_28'))

    def test_rental_eliminated_or_scrapped_equipment_cannot_be_rehabilitated_by_paperwork(self):
        self.assertIn('补齐维护检验资料不能使淘汰或报废设备恢复出租资格', hazard(RENTAL)['conditions'])
        self.assertIn('国家明令淘汰和已经报废的特种设备', source_text('TSE_28'))

    def test_occupational_health_scope_is_hazard_employer_workplaces_not_only_hazard_room(self):
        text = hazard(HEALTH)['conditions']
        self.assertIn('产生职业病危害的用人单位的工作场所', text)
        self.assertIn('单位层级适用范围不缩为仅产生危害的某个房间', text)
        self.assertIn('劳动者进行职业活动的所有地点，包括建设单位施工场所', source_text('NHC_57_workplace'))
        self.assertNotIn('所有用人单位的全部财产', text)
        self.assertEqual(hazard(HEALTH)['places'], ['产生职业病危害的用人单位的工作场所'])

    def test_workplace_separation_and_no_residence_are_independent_without_medical_data_gate(self):
        text = hazard(HEALTH)['conditions']
        self.assertIn('工作场所与生活场所分开、工作场所不得住人', text)
        self.assertIn('本项核查布局及实际用途', text)
        self.assertIn('不要求收集个人病历、健康检查结果等无关信息', text)
        self.assertIn('工作场所与生活场所分开，工作场所不得住人', source_text('NHC_12'))
        self.assertNotIn('未分开且已住人时才', text)

    def test_blind_rescue_requires_an_actual_or_ongoing_event_not_training_inference(self):
        text = hazard(RESCUE)['conditions']
        self.assertIn('工贸企业有限空间作业中发生未做好安全措施盲目施救行为', text)
        self.assertIn('核查监护人员是否予以制止', text)
        self.assertIn('平时预案、培训或演练不能证明曾发生该事件', text)
        self.assertNotIn('已造成人员伤亡', text)
        self.assertNotIn('仅限原作业人员施救', text)
        self.assertIn('未做好安全措施盲目施救的，监护人员应当予以制止', source_text(RESCUE))

    def test_blind_rescue_review_never_authorizes_dangerous_test_or_unprotected_entry(self):
        text = hazard(RESCUE)['conditions']
        self.assertIn('不得为核验而制造危险救援', text)
        self.assertIn('监护职责不赋予未经安全保障进入有限空间救援的许可', text)
        excerpts = '\n'.join(FIXTURE['statutoryText'][RESCUE]['completeOfficialExcerptParts'])
        self.assertIn('未被设计为固定工作场所', excerpts)
        self.assertIn('冶金、有色、建材、机械、轻工、纺织、烟草、商贸', excerpts)

    def test_hotwork_restart_checks_planned_and_actual_restart_without_compliance_precondition(self):
        text = hazard(RESTART)['conditions']
        self.assertIn('仅适用于粉尘涉爆工贸企业', text)
        self.assertIn('设备设施或除尘系统实施动火检修维修后拟恢复或已经恢复生产', text)
        self.assertIn('作业后须妥善清理现场', text)
        self.assertIn('作业点最高温度恢复常温后方可重新开始生产', text)
        self.assertIn('本项不因普通粉尘或普通动火场景而直接适用', text)
        self.assertNotIn('已经完成清理且温度合格的复产', text)
        self.assertIn('作业点最高温度恢复到常温后方可重新开始生产', source_text(RESTART))

    def test_jiangsu_transit_has_four_shop_zones_but_wider_facility_material_scope(self):
        text = hazard(TRANSIT)['conditions']
        self.assertIn('仅适用于江苏省行政区域内城市轨道交通', text)
        self.assertIn('车站站台层、站厅付费区、乘客疏散区以及疏散通道不得设置商铺', text)
        self.assertIn('运营设施和广告设施应采用不燃、难燃材料', text)
        self.assertIn('不得扩大为车站全部商业区域一律禁设商铺', text)
        self.assertIn('也不得把难燃材料一概排除', text)
        self.assertNotIn('上述四类区域的运营设施', text)
        self.assertNotIn('商铺违规且材料不合格', text)
        self.assertIn('铁路、港航、民航、林业系统的消防工作，按照国家有关规定执行',
                      '\n'.join(FIXTURE['statutoryText'][TRANSIT]['completeOfficialExcerptParts']))


if __name__ == '__main__':
    unittest.main()
