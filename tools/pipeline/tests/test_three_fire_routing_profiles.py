"""Regress the three independently reviewed Jiangsu non-onsite routes.

These tests read accepted records/reviews and copy their exact source closure into
temporary directories for negative checks. They never author or renew an approval.
Routing is not a legal inference engine: no per-use facts, missing-document flag,
or unfinished review window can become an observed violation through this API.
"""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools' / 'v4'))
from field_profiles import (CHECKS, PUBLIC_FIELDS, ProfileContext, digest,
                            public_projection, review_bindings, validate_profile)

KNOWLEDGE = ROOT / 'knowledge'
AS_OF = date(2026, 9, 30)
REVIEWED_HASHES = {
    'FPR_ROUTING_JSXF_53_3': '2e76740906ebd94050d6e4cffbdd185b4bf005de1318bfefbcbf11ec74292c73',
    'FPR_ROUTING_JSXF_58_1': '7d68356767522e39fda24d2d56ca03662063c629d1c8964b4268355d5b4d961c',
    'FPR_ROUTING_JSXF_58_2': '26604ad9a1676e66a46b56420d5984639b08e5b74848e6b338151b8f7a4d03e1',
}
LEGACY_FILE_HASHES = {
    'records/FPR_EXTINGUISHER_ACCESS_BLOCKED.json': '5563b7fcebd32d4cb9d946a9943d9f4a00ee583102337677d0e355fcd912b3cc',
    'records/FPR_EXTINGUISHER_BRACKET_OBSTRUCTION.json': '92391af878037b9b7fea5d0197da46a95bbf8032069db31c0a0b54094882da5d',
    'records/FPR_GAS_ALARM_FUNCTION_FAILURE.json': '228f81cd5fbb54c07004472b2072f4f54c157a731ea22792a9e9943b4509cfd8',
    'reviews/FPR_EXTINGUISHER_ACCESS_BLOCKED.json': 'ea5888c513c58b0f318fdc57c21d439f9bc04155fc271a6055b5cfe23d270160',
    'reviews/FPR_EXTINGUISHER_BRACKET_OBSTRUCTION.json': 'c9e592e9147a888c17dda8a8a527b856125e1b061200b9ae34ba16b5a3e58a3e',
    'reviews/FPR_GAS_ALARM_FUNCTION_FAILURE.json': '01ccb3872cd871a865b735a87603d3efa65667a3817e0c73e4283719295351f3',
}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(root, rel, obj):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')


class ThreeFireRoutingProfilesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = ProfileContext(KNOWLEDGE)
        cls.profiles = {ident: read(KNOWLEDGE / 'field-profiles/v1/records' / (ident + '.json'))
                        for ident in REVIEWED_HASHES}
        cls.reviews = {ident: read(KNOWLEDGE / 'field-profiles/v1/reviews' / (ident + '.json'))
                       for ident in REVIEWED_HASHES}

    def snapshot(self, ident):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        profile = self.profiles[ident]
        for key, obj in self.context.dependencies(profile).items():
            if key != 'associationIds':
                self.assertIsNotNone(obj, key)
                write(root, key + '.json', obj)
        write(root, 'field-profiles/v1/records/' + ident + '.json', profile)
        write(root, 'field-profiles/v1/reviews/' + ident + '.json', self.reviews[ident])
        return root

    def assert_blocked(self, root, ident, reason):
        result = public_projection(root, as_of=AS_OF)
        self.assertFalse(result['public']['records'])
        excluded = {r['profileId']: r['reasons'] for r in result['inventory']['excludedProfiles']}
        self.assertIn(reason, excluded[ident])

    def test_only_exact_independently_reviewed_bytes_are_accepted(self):
        for ident, profile in self.profiles.items():
            with self.subTest(profile=ident):
                self.assertEqual(validate_profile(profile), [])
                self.assertEqual(digest(profile), REVIEWED_HASHES[ident])
                review = self.reviews[ident]
                self.assertEqual(review['semanticChecks'], {key: True for key in CHECKS})
                self.assertEqual(set(review['basisScopeReasons']), set(profile['basisLinkIds']))
                for key, value in review_bindings(profile, self.context).items():
                    self.assertEqual(review[key], value)
                self.assertEqual(review['reviewEvidence']['formalReviewReportSha256'],
                                 '608641558111fd60a65691e446824c9b67e0edb727bd466c15267fa3c9e6feba')

    def test_original_three_onsite_records_and_reviews_are_byte_unchanged(self):
        for rel, expected in LEGACY_FILE_HASHES.items():
            with self.subTest(path=rel):
                path = KNOWLEDGE / 'field-profiles/v1' / rel
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)

    def test_jurisdiction_and_responsible_subject_stay_in_every_public_route(self):
        expected_subject = {'FPR_ROUTING_JSXF_53_3': '业主和物业使用人',
                            'FPR_ROUTING_JSXF_58_1': '学校及其他教育机构',
                            'FPR_ROUTING_JSXF_58_2': '消防安全重点单位'}
        for ident, subject in expected_subject.items():
            row = public_projection(self.snapshot(ident), as_of=AS_OF)['public']['records'][0]
            self.assertEqual(row['defaultFieldEntry'], 'exclude')
            for text in [row['sourceHazard']['conditions'], row['bases'][0]['applicability'],
                         row['applicability']['requires'][0]]:
                self.assertIn('江苏省行政区域内', text)
                self.assertIn(subject, text)
            self.assertEqual(row['bases'][0]['jurisdictionCode'], 'CN-32')
            self.assertEqual(row['bases'][0]['lawJurisdictionCode'], 'CN-32')

    def test_prevention_is_not_upgraded_to_prohibition_or_property_company_duty(self):
        p = self.profiles['FPR_ROUTING_JSXF_53_3']
        self.assertEqual(p['inspectionClass'], 'legal_obligation')
        self.assertEqual(p['contentDisposition'], 'legal_obligation')
        self.assertIn('避免进入', p['title'])
        self.assertIn('不能将其改写为省级统一“禁止进入”', p['applicability']['requires'][0])
        self.assertIn('第53条第三款第一句', p['applicability']['requires'][1])
        self.assertIn('不认定物业服务企业未劝阻', p['applicability']['excludes'][0])
        self.assertIn('不混用南京条例', p['applicability']['excludes'][1])
        self.assertIn('避免将其带入住宅电梯和户内', p['correctiveDirection'])
        self.assertNotIn('禁止将其带入', p['correctiveDirection'])

    def test_school_visits_and_evacuation_remain_separate_without_half_year_rule(self):
        p = self.profiles['FPR_ROUTING_JSXF_58_1']
        self.assertEqual(p['inspectionClass'], 'document_review')
        self.assertIn('visitArrangementsAndExecutionConfirmed', p['applicability']['perUseFacts'])
        self.assertIn('evacuationDrillArrangementsAndExecutionConfirmed', p['applicability']['perUseFacts'])
        self.assertIn('不预设半年频次', p['applicability']['requires'][3])
        self.assertIn('不把重点单位第二款每半年一次自动套用于所有学校',
                      p['applicability']['excludes'][0])
        self.assertIn('分别核对参观及疏散演练', p['evidenceRequirements'][0])
        self.assertIn('定期', p['correctiveDirection'])
        self.assertNotIn('半年', p['correctiveDirection'])

    def test_key_unit_status_half_year_windows_and_both_contents_are_required(self):
        p = self.profiles['FPR_ROUTING_JSXF_58_2']
        self.assertIn('先确认其重点单位属性', p['applicability']['requires'][0])
        self.assertIn('符合消防安全重点单位界定标准的个体工商户',
                      p['applicability']['requires'][0])
        self.assertIn('halfYearReviewWindowConfirmed', p['applicability']['perUseFacts'])
        self.assertIn('firefightingAndEvacuationContentConfirmed', p['applicability']['perUseFacts'])
        self.assertIn('逐个半年核至少一次灭火和应急疏散演练', p['applicability']['requires'][3])
        self.assertIn('全年两次不能自动替代每半年至少一次', p['applicability']['excludes'][1])

    def test_unelapsed_windows_and_missing_documents_never_become_auto_findings(self):
        # The route API has no per-use fact input/evaluator. Explicit review
        # constraints plus permanently false observedViolation preserve that
        # boundary; this test does not pretend to validate real drill events.
        for ident, p in self.profiles.items():
            with self.subTest(profile=ident):
                root = self.snapshot(ident)
                now = public_projection(root, as_of=AS_OF)['public']['records']
                later = public_projection(root, as_of=date(2026, 10, 1))['public']['records']
                self.assertEqual(now, later)
                row = now[0]
                self.assertEqual(row['profileKind'], 'routing_only')
                self.assertIsNone(row['findingTemplate'])
                self.assertIs(row['observedViolation'], False)
                self.assertNotEqual(row['contentDisposition'], 'onsite_finding')
                self.assertTrue(all(isinstance(f, str) for f in row['applicability']['perUseFacts']))
                self.assertNotIn('defectObserved', row['applicability']['perUseFacts'])
                constraints = ' '.join(self.reviews[ident]['reviewEvidence']['commonInterpretiveBoundaries'])
                self.assertIn('资料缺失与未实际履职必须区分', constraints)
        constraints = ' '.join(self.reviews['FPR_ROUTING_JSXF_58_2']['reviewEvidence']['usageConstraints'])
        self.assertIn('不对未到期期间提前认定未履职', constraints)

    def test_missing_review_blocks_each_exact_profile(self):
        for ident in self.profiles:
            with self.subTest(profile=ident):
                root = self.snapshot(ident)
                (root / 'field-profiles/v1/reviews' / (ident + '.json')).unlink()
                self.assert_blocked(root, ident, 'PROFILE_REVIEW_MISSING')

    def test_evidence_and_unselected_association_drift_invalidate_review(self):
        for ident, p in self.profiles.items():
            for drift in ('evidence', 'unselected_association'):
                with self.subTest(profile=ident, drift=drift):
                    root = self.snapshot(ident)
                    if drift == 'evidence':
                        path = root / 'evidence/E_FIRE_CORRECTION_JSXF_20260930.json'
                        evidence = read(path)
                        evidence['snapshotSha256'] = 'test-only changed evidence'
                        write(root, str(path.relative_to(root)), evidence)
                    else:
                        link = copy.deepcopy(self.context.entities['links'][p['basisLinkIds'][0]])
                        link.update(id='K_TEST_UNSELECTED_DRIFT', role='supporting', lifecycle='proposed')
                        write(root, 'links/' + link['id'] + '.json', link)
                    self.assert_blocked(root, ident, 'PROFILE_REVIEW_STALE:dependencyFingerprint')

    def test_scope_widening_cannot_reuse_the_accepted_review(self):
        for ident in self.profiles:
            root = self.snapshot(ident)
            p = copy.deepcopy(self.profiles[ident])
            p['applicability']['requires'][0] = '全国全部单位，无条件适用'
            write(root, 'field-profiles/v1/records/' + ident + '.json', p)
            self.assert_blocked(root, ident, 'PROFILE_REVIEW_STALE:reviewedProfileHash')

    def test_public_routes_do_not_leak_review_draft_metadata_or_private_facts(self):
        forbidden = {'reviewer', 'reason', 'reviewEvidence', 'formalReviewReportSha256',
                     'auditOnly', 'formalApproval', 'productionAdmissionReady', 'sourceCommit',
                     'authoringRationale', 'sourceHazardContentHash', 'semanticChecks'}
        for ident in self.profiles:
            row = public_projection(self.snapshot(ident), as_of=AS_OF)['public']['records'][0]
            self.assertEqual(set(row), PUBLIC_FIELDS | {'recordKind', 'observedViolation',
                                                        'sourceHazard', 'bases'})
            self.assertFalse(forbidden & set(row))
            text = json.dumps(row, ensure_ascii=False)
            for private_path in ('/workspace/', '/Users/', '/home/', 'file://'):
                self.assertNotIn(private_path, text)


if __name__ == '__main__':
    unittest.main()
