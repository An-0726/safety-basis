"""Synthetic-only governance tests. No real approvals or pilot fixtures written."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4'))
from canonical import content_hash
from field_profiles import (CHECKS, FIELDS, PROFILE_ROOT, ProfileContext, public_projection,
                            review_bindings, validate_profile)

AS_OF = date(2026, 9, 30)


class FieldProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.law = {'id': 'LF_TEST', 'canonicalName': 'Synthetic law', 'issuer': 'Synthetic issuer', 'jurisdictionCode': 'CN'}
        self.version = {'id': 'LV_TEST', 'lawId': self.law['id'], 'versionKey': 'synthetic', 'effectiveDate': '2020-01-01', 'endDate': '2026-10-01', 'validityStatus': 'active'}
        self.clause = {'id': 'C_TEST', 'lawVersionId': self.version['id'], 'articlePath': '1', 'quote': '1 Synthetic requirement'}
        self.hazard = {'id': 'H_TEST', 'title': 'Synthetic hazard', 'description': 'Synthetic description', 'measures': 'Synthetic measures', 'category': 'Synthetic', 'lifecycle': 'active'}
        self.link = {'id': 'K_TEST', 'hazardId': self.hazard['id'], 'clauseId': self.clause['id'], 'role': 'direct', 'lifecycle': 'active', 'applicability': 'Synthetic scope'}
        self.put('evidence/E_TEST.json', {'id': 'E_TEST', 'snapshotSha256': 'synthetic'})
        for kind, entity in [('laws', self.law), ('law-versions', self.version), ('clauses', self.clause), ('hazards', self.hazard), ('links', self.link)]:
            self.entity(kind, entity)
        self.profile = {'schemaVersion': 1, 'id': 'FPR_TEST', 'revision': 1,
                        'hazardId': self.hazard['id'], 'title': 'Reusable synthetic finding',
                        'inspectionClass': 'core_onsite_inspection', 'defaultFieldEntry': 'conditional',
                        'contentDisposition': 'onsite_finding',
                        'applicability': {'requires': ['Relevant equipment is within scope'],
                                          'excludes': ['Different equipment category'],
                                          'perUseFacts': ['applicableRequirementConfirmed', 'siteTriggerConfirmed', 'defectObserved']},
                        'findingTemplate': {'text': 'At {{location}}, {{object}} has {{defect}}.',
                                            'slots': [{'key': x, 'label': x.title()} for x in ('location', 'object', 'defect')]},
                        'evidenceRequirements': ['Onsite observation and applicable requirement'],
                        'correctiveDirection': 'Restore required condition and verify it',
                        'basisLinkIds': [self.link['id']]}
        self.save_profile()
        self.approve_synthetic()

    def put(self, rel, value):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def entity(self, kind, value):
        self.put(f"{kind}/{value['id']}.json", value)
        review = {'entityId': value['id'], 'decision': 'verified', 'reviewedContentHash': content_hash(value), 'evidenceRefs': ['E_TEST']}
        if kind == 'links':
            review.update(reason='Synthetic applicability reviewed', contextHashes={'hazard': content_hash(self.hazard), 'clause': content_hash(self.clause)})
        self.put(f"reviews/{kind}/{value['id']}.json", review)

    def save_profile(self):
        self.put(f"{PROFILE_ROOT}/records/{self.profile['id']}.json", self.profile)

    def approve_synthetic(self):
        self.review = {'schemaVersion': 1, 'entityId': self.profile['id'], 'profileRevision': self.profile['revision'],
                       'decision': 'verified', 'reviewer': 'Synthetic test only', 'reviewedOn': AS_OF.isoformat(),
                       'reason': 'Synthetic semantic verification',
                       'basisScopeReasons': {key: 'Synthetic profile scope is contained by this exact basis' for key in self.profile['basisLinkIds']}, 'semanticChecks': {x: True for x in CHECKS},
                       **review_bindings(self.profile, self.root)}
        self.save_review()

    def save_review(self):
        # Independently named review files exercise entityId-based lookup.
        self.put(f"{PROFILE_ROOT}/reviews/RV_{self.profile['id']}.json", self.review)

    def project(self, at=AS_OF):
        return public_projection(self.root, as_of=at)

    def blocked(self, reason):
        out = self.project()
        self.assertEqual(out['public']['records'], [])
        self.assertTrue(any(reason in r for item in out['inventory']['excludedProfiles'] for r in item['reasons']), out)

    def test_template_approval_has_no_current_enterprise_facts(self):
        out = self.project()
        self.assertEqual(out['inventory']['publishedCount'], 1)
        self.assertFalse(out['public']['records'][0]['observedViolation'])
        self.assertIn('defectObserved', out['public']['records'][0]['applicability']['perUseFacts'])
        self.assertEqual(out, self.project())

    def test_profile_edit_and_revision_stale_review(self):
        self.profile['title'] = 'Changed meaning'
        self.save_profile()
        self.blocked('PROFILE_REVIEW_STALE:reviewedProfileHash')
        self.profile['revision'] += 1
        self.save_profile()
        self.blocked('PROFILE_REVIEW_IDENTITY')

    def test_all_upstream_content_and_review_changes_invalidate(self):
        for rel in ('hazards/H_TEST.json', 'links/K_TEST.json', 'clauses/C_TEST.json', 'law-versions/LV_TEST.json', 'laws/LF_TEST.json', 'evidence/E_TEST.json', 'reviews/links/K_TEST.json'):
            with self.subTest(rel=rel):
                path = self.root / rel
                before = path.read_bytes()
                obj = json.loads(before)
                obj['syntheticChange'] = True
                self.put(rel, obj)
                self.blocked('PROFILE_REVIEW_STALE:dependencyFingerprint')
                path.write_bytes(before)

    def test_link_addition_removal_invalidate_even_unselected_proposed(self):
        link = {**self.link, 'id': 'K_ADDED', 'lifecycle': 'proposed'}
        self.entity('links', link)
        self.blocked('PROFILE_REVIEW_STALE:dependencyFingerprint')
        self.approve_synthetic()
        self.assertEqual(self.project()['inventory']['publishedCount'], 1)
        (self.root / 'links/K_ADDED.json').unlink()
        self.blocked('PROFILE_REVIEW_STALE:dependencyFingerprint')

    def test_date_expiry_rechecks_gate_without_content_change(self):
        self.assertEqual(self.project(date(2026, 9, 30))['inventory']['publishedCount'], 1)
        out = self.project(date(2026, 10, 1))
        self.assertEqual(out['public']['records'], [])
        self.assertIn('SELECTED_BASIS_GATE_FAILED:K_TEST', out['inventory']['excludedProfiles'][0]['reasons'])

    def test_malformed_selected_version_dates_never_mean_unbounded_validity(self):
        for key in ('effectiveDate', 'endDate'):
            original = self.version[key]
            for value in ('2026-09-xx', '2026-02-30', '20260930', '2026-W40-3', ' 2026-09-30', 0, False, [], {}):
                with self.subTest(key=key, value=value):
                    self.version[key] = value
                    self.entity('law-versions', self.version)
                    self.approve_synthetic()
                    self.blocked('SELECTED_VERSION_DATE_INVALID:' + key)
            self.version[key] = original

    def test_selected_version_exclusive_end_must_follow_start(self):
        for end in ('2020-01-01', '2019-12-31'):
            self.version['endDate'] = end
            self.entity('law-versions', self.version)
            self.approve_synthetic()
            self.blocked('SELECTED_VERSION_DATE_RANGE_INVALID')
        for end in (None, ''):
            self.version['endDate'] = end
            self.entity('law-versions', self.version)
            self.approve_synthetic()
            self.assertEqual(self.project()['inventory']['publishedCount'], 1)
        del self.version['endDate']
        self.entity('law-versions', self.version)
        self.approve_synthetic()
        self.assertEqual(self.project()['inventory']['publishedCount'], 1)

    def test_explicit_selected_review_dates_cannot_be_future_or_malformed(self):
        for kind, ident in (('hazards', 'H_TEST'), ('links', 'K_TEST'), ('clauses', 'C_TEST'), ('law-versions', 'LV_TEST'), ('laws', 'LF_TEST')):
            path = self.root / f'reviews/{kind}/{ident}.json'
            original = json.loads(path.read_text())
            for field in ('checkedAt', 'reviewedAt', 'reviewedOn'):
                for value, reason in (('2027-09-30T00:00:00+00:00', 'FUTURE'), ('2026-10-01', 'FUTURE'), ('2026-09-xx', 'INVALID'), ('2026-02-30T00:00:00Z', 'INVALID'), (None, 'INVALID'), (42, 'INVALID')):
                    with self.subTest(kind=kind, field=field, value=value):
                        self.put(f'reviews/{kind}/{ident}.json', {**original, field: value})
                        self.approve_synthetic()
                        self.blocked('SELECTED_REVIEW_DATE_' + reason + ':' + field)
            self.put(f'reviews/{kind}/{ident}.json', original)

    def test_review_dates_use_written_calendar_day_and_missing_legacy_is_ok(self):
        path = self.root / 'reviews/clauses/C_TEST.json'
        original = json.loads(path.read_text())
        for value in ('2026-09-30', '2026-09-30T23:59:59-12:00', '2026-09-29T12:00:00Z'):
            self.put('reviews/clauses/C_TEST.json', {**original, 'checkedAt': value})
            self.approve_synthetic()
            self.assertEqual(self.project()['inventory']['publishedCount'], 1)
        self.put('reviews/clauses/C_TEST.json', original)
        self.approve_synthetic()
        self.assertEqual(self.project()['inventory']['publishedCount'], 1)
        # Unselected association metadata is bound but its date does not become a
        # selected-chain requirement; only the independent semantic review gates it.
        self.entity('links', {**self.link, 'id': 'K_UNSELECTED'})
        self.put('reviews/links/K_UNSELECTED.json', {'checkedAt': '2027-01-01'})
        self.approve_synthetic()
        self.assertEqual(self.project()['inventory']['publishedCount'], 1)

    def test_missing_selected_data_including_evidence_fails_closed(self):
        for rel in ('hazards/H_TEST.json', 'links/K_TEST.json', 'clauses/C_TEST.json', 'evidence/E_TEST.json'):
            with self.subTest(rel=rel):
                path = self.root / rel
                before = path.read_bytes()
                path.unlink()
                self.blocked('PROFILE_DEPENDENCY_MISSING')
                path.write_bytes(before)

    def test_unreviewed_unknown_and_incomplete_review_excluded(self):
        (self.root / f'{PROFILE_ROOT}/reviews/RV_FPR_TEST.json').unlink()
        self.blocked('PROFILE_REVIEW_MISSING')
        self.review['semanticChecks']['applicability'] = False
        self.save_review()
        self.blocked('PROFILE_SEMANTIC_REVIEW_INCOMPLETE')
        self.review['decision'] = 'reviewed_candidate'
        self.save_review()
        self.blocked('PROFILE_REVIEW_NOT_VERIFIED')
        self.profile.update(inspectionClass='undetermined', defaultFieldEntry='undetermined', contentDisposition='undetermined', findingTemplate=None)
        self.save_profile()
        self.approve_synthetic()
        self.blocked('PROFILE_UNDETERMINED')

    def test_proposed_hazard_and_selected_link_isolation(self):
        self.hazard['lifecycle'] = 'proposed'
        self.entity('hazards', self.hazard)
        self.approve_synthetic()
        self.blocked('SOURCE_HAZARD_GATE_FAILED')
        self.hazard['lifecycle'] = 'active'
        self.entity('hazards', self.hazard)
        self.link['lifecycle'] = 'proposed'
        self.entity('links', self.link)
        self.approve_synthetic()
        self.blocked('SELECTED_BASIS_GATE_FAILED')

    def test_selected_link_must_qualify_and_belong_to_source(self):
        self.link['role'] = 'supporting'
        self.entity('links', self.link)
        self.approve_synthetic()
        self.blocked('SELECTED_BASIS_GATE_FAILED')
        self.link['role'] = 'fallback'
        self.entity('links', self.link)
        self.approve_synthetic()
        self.assertEqual(self.project()['inventory']['publishedCount'], 1)
        self.link['hazardId'] = 'H_OTHER'
        self.entity('links', self.link)
        self.approve_synthetic()
        self.blocked('SELECTED_BASIS_GATE_FAILED')

    def test_document_legal_counterexample_routes_never_onsite(self):
        for disposition, cls in [('document_check', 'document_review'), ('legal_obligation', 'legal_obligation'), ('counterexample', 'special_review'), ('special_check', 'special_review')]:
            with self.subTest(disposition=disposition):
                self.profile.update(contentDisposition=disposition, inspectionClass=cls, defaultFieldEntry='exclude', findingTemplate=None)
                self.save_profile()
                self.approve_synthetic()
                row = self.project()['public']['records'][0]
                self.assertIsNone(row['findingTemplate'])
                self.assertFalse(row['observedViolation'])
                self.profile['defaultFieldEntry'] = 'include'
                self.assertIn('PROFILE_NON_ONSITE_ENTRY', validate_profile(self.profile))

    def test_private_metadata_is_not_public_and_private_paths_rejected(self):
        self.profile['internalNotes'] = {'enterprise': 'private', 'path': '/home/private/file'}
        self.save_profile()
        self.approve_synthetic()
        row = self.project()['public']['records'][0]
        self.assertEqual(set(row), FIELDS | {'recordKind', 'observedViolation', 'bases', 'sourceHazard'})
        self.assertNotIn('private', json.dumps(row))
        self.assertNotIn('reviewer', json.dumps(self.project()['public']))
        self.profile['title'] = '/workspace/private/data'
        self.assertIn('PROFILE_PRIVATE_TEXT', validate_profile(self.profile))
        self.profile['applicability']['secret'] = 'hidden'
        self.assertIn('PROFILE_APPLICABILITY', validate_profile(self.profile))

    def test_variable_counts_missing_profiles_and_pilot_not_read(self):
        self.put('hazards/H_NO_PROFILE.json', {**self.hazard, 'id': 'H_NO_PROFILE'})
        self.put('field-profiles-pilot/records/FP_P01.json', {'invalid': 'deliberately ignored'})
        self.assertEqual(self.project()['inventory']['hazardsWithoutProfiles'], ['H_NO_PROFILE'])
        for index in range(30):
            self.profile['id'] = f'FPR_{index:03d}'
            self.save_profile()
            self.approve_synthetic()
        self.assertEqual(self.project()['inventory']['publishedCount'], 31)
        for path in (self.root / PROFILE_ROOT / 'records').glob('*.json'):
            path.unlink()
        out = self.project()
        self.assertEqual(out['public']['records'], [])
        self.assertEqual(out['inventory']['profileCount'], 0)
        self.assertEqual(len(out['inventory']['orphanReviewIds']), 31)

    def test_duplicate_ids_and_invalid_json_abort(self):
        self.put(f'{PROFILE_ROOT}/records/duplicate.json', self.profile)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.project()
        (self.root / PROFILE_ROOT / 'records/duplicate.json').write_text('{')
        with self.assertRaises(ValueError):
            self.project()

    def test_invalid_types_missing_fields_and_placeholders(self):
        for key in FIELDS:
            bad = copy.deepcopy(self.profile)
            del bad[key]
            self.assertTrue(validate_profile(bad), key)
        for key in ('inspectionClass', 'defaultFieldEntry', 'contentDisposition'):
            bad = copy.deepcopy(self.profile)
            bad[key] = {}
            self.assertTrue(validate_profile(bad), key)
        bad = copy.deepcopy(self.profile)
        bad['findingTemplate']['text'] += ' {{undeclared}}'
        self.assertIn('PROFILE_TEMPLATE_PLACEHOLDERS', validate_profile(bad))
        with self.assertRaises(TypeError):
            public_projection(self.root, as_of='2026-09-30')

    def test_exact_scope_review_and_public_restrictions(self):
        self.review['basisScopeReasons'] = {}
        self.save_review()
        self.blocked('PROFILE_SCOPE_REVIEW_INCOMPLETE')
        self.link.update(applicability='Only activated-carbon VOC equipment', jurisdictionCode='CN-32')
        self.entity('links', self.link)
        self.approve_synthetic()
        basis = self.project()['public']['records'][0]['bases'][0]
        self.assertEqual(basis['applicability'], self.link['applicability'])
        self.assertEqual(basis['jurisdictionCode'], 'CN-32')
        self.assertEqual(basis['lawJurisdictionCode'], 'CN')
        self.assertEqual(basis['linkId'], 'K_TEST')
        self.link['applicability'] = '/home/private/company'
        self.entity('links', self.link)
        self.approve_synthetic()
        self.blocked('SELECTED_BASIS_PUBLIC_TEXT_UNSAFE')

    def test_source_hazard_conditions_cannot_be_lost(self):
        self.hazard['conditions'] = 'Only E-class electrical fires in the specified region'
        self.entity('hazards', self.hazard)
        self.entity('links', self.link)
        self.approve_synthetic()
        source = self.project()['public']['records'][0]['sourceHazard']
        self.assertEqual(source, {'id': 'H_TEST', 'title': self.hazard['title'], 'conditions': self.hazard['conditions']})
        self.hazard['conditions'] = '/home/private/company'
        self.entity('hazards', self.hazard)
        self.entity('links', self.link)
        self.approve_synthetic()
        self.blocked('SOURCE_HAZARD_PUBLIC_TEXT_UNSAFE')

    def test_malformed_evidence_refs_fail_closed_predictably(self):
        for refs in (None, 'E_TEST', [None], [42], [{}], [{'id': []}]):
            self.put('reviews/clauses/C_TEST.json', {'evidenceRefs': refs})
            with self.assertRaisesRegex(ValueError, 'invalid evidence'):
                self.project()

    def test_legacy_unicode_and_spaced_evidence_ids_are_preserved(self):
        self.hazard['id'] = 'H_JS140_十八_2'
        self.entity('hazards', self.hazard)
        self.link['hazardId'] = self.hazard['id']
        self.entity('links', self.link)
        self.profile['hazardId'] = self.hazard['id']
        eid = 'E_财资〔2022〕 GB 12158'
        self.put('evidence/' + eid + '.json', {'id': eid})
        path = self.root / 'reviews/laws/LF_TEST.json'
        review = json.loads(path.read_text())
        review['evidenceRefs'] = [eid]
        self.put('reviews/laws/LF_TEST.json', review)
        self.save_profile()
        self.approve_synthetic()
        self.assertEqual(self.project()['public']['records'][0]['hazardId'], self.hazard['id'])
        for ident in ('', '../bad', '/bad', 'bad\\path', 'bad\x00', 'bad\n'):
            self.put('evidence/INVALID.json', {'id': ident})
            with self.assertRaisesRegex(ValueError, 'invalid'):
                ProfileContext(self.root)

    def test_real_namespace_legacy_identity_compatibility(self):
        root = Path(__file__).resolve().parents[3] / 'knowledge'
        context = ProfileContext(root)
        self.assertIn('H_JS140_十八_2', context.entities['hazards'])
        self.assertIn('E_12158_GB 12158', context.entities['evidence'])
        result = public_projection(root, as_of=AS_OF)
        self.assertEqual(result['inventory']['publishedCount'], len(result['public']['records']))

    def test_future_review_is_not_accepted(self):
        self.review['reviewedOn'] = '2026-10-01'
        self.save_review()
        self.blocked('PROFILE_REVIEW_FUTURE')


if __name__ == '__main__':
    unittest.main()
