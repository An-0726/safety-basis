"""Synthetic-only controlled catalog / direct topic and release regression tests."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4'))
from canonical import content_hash
from field_profiles import ProfileContext
import major_criteria as major
import check_major_criteria as validator
import release_snapshot
import validate_all
import test_field_profiles as fixtures
import test_field_profile_release as release_fixtures


def synthetic_config(f):
    """Only a synthetic test fixture; never writes production approvals."""
    f.version.update(documentNumber='Synthetic 1', sourceUrl='https://example.gov.cn/standard')
    f.entity('law-versions', f.version)
    context = ProfileContext(f.root)
    return {'schemaVersion': 1, 'standards': [{
        'lawVersionId': f.version['id'],
        'identity': {'lawId': f.law['id'], 'name': f.law['canonicalName'],
                     'documentNumber': f.version['documentNumber'], 'versionKey': f.version['versionKey'],
                     'officialSourceUrl': f.version['sourceUrl']},
        'lawContentHash': content_hash(f.law), 'versionContentHash': content_hash(f.version),
        'officialScope': {'label': 'Synthetic selected scope only',
                          'sourceUrls': [f.version['sourceUrl']], 'wholeStandardComplete': False},
        'scopeVerified': True, 'expectedJudgmentItemCount': 1,
        'clauses': [{'clauseId': f.clause['id'], 'contentHash': content_hash(f.clause),
                     'granularity': 'whole_clause', 'judgmentItemCount': 1}],
        'topicLinks': [{'linkId': f.link['id'], 'hazardId': f.hazard['id'], 'clauseId': f.clause['id'],
                        'dependencyFingerprint': context.fingerprint({'hazardId': f.hazard['id'], 'basisLinkIds': [f.link['id']]})}],
        'pendingTopicLinks': []}]}


class MajorCriteriaTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.FieldProfileTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.config = synthetic_config(self.f)
        self.save()

    def save(self):
        self.f.put(major.CONFIG_PATH, self.config)

    def project(self, at=date(2026, 9, 30)):
        return major.public_projection(self.root, as_of=at)

    def standard(self):
        return self.project()['catalog']['standards'][0]

    def test_independent_catalog_and_topic(self):
        row = self.standard()
        self.assertEqual(row['coverage']['reviewedWholeClauseCount'], 1)
        self.assertEqual(row['coverage']['reviewedSubitemClauseCount'], 0)
        self.assertEqual(row['coverage']['status'], 'reviewed_scope_complete')
        self.assertEqual(row['directHazardCount'], 1)
        self.assertFalse(row['coverage']['wholeStandardComplete'])
        self.assertTrue(self.project()['catalog']['wholeNormNotFieldFinding'])
        self.assertFalse(self.project()['catalog']['allIndustryCoverage'])
        self.assertEqual(self.project(), self.project())

    def test_clause_without_any_hazard_is_published_without_creating_one(self):
        (self.root / 'links/K_TEST.json').unlink()
        (self.root / 'hazards/H_TEST.json').unlink()
        row = self.standard()
        self.assertEqual(len(row['clauses']), 1)
        self.assertEqual(row['directHazardCount'], 0)
        self.assertEqual(self.project()['topic']['hazardIds'], [])
        self.assertFalse((self.root / 'hazards/H_TEST.json').exists())

    def test_unreviewed_and_missing_or_stale_clause_review_fail_closed(self):
        p = self.root / 'reviews/clauses/C_TEST.json'
        original = json.loads(p.read_text())
        for change in ({'decision': 'proposed'}, {'reviewedContentHash': '0' * 64}, None):
            if change is None:
                p.unlink()
            else:
                self.f.put('reviews/clauses/C_TEST.json', {**original, **change})
            self.assertEqual(self.project()['catalog']['standards'], [])

    def test_newly_resigned_content_does_not_reuse_catalog_semantic_selection(self):
        self.f.clause['quote'] = '1 Different requirement, not the controlled wording'
        self.f.entity('clauses', self.f.clause)
        self.assertEqual(self.project()['catalog']['standards'], [])

    def test_expiry_future_and_malformed_dates(self):
        self.assertEqual(self.project(date(2026, 10, 1))['catalog']['standards'], [])
        self.assertEqual(self.project(date(2019, 12, 31))['catalog']['standards'], [])
        for end in ('nonsense', False, [], '2019-01-01'):
            self.f.version['endDate'] = end
            self.f.entity('law-versions', self.f.version)
            self.config['standards'][0]['versionContentHash'] = content_hash(self.f.version)
            self.save()
            self.assertEqual(self.project()['catalog']['standards'], [])

    def test_explicit_future_or_malformed_review_dates(self):
        p = 'reviews/clauses/C_TEST.json'
        original = json.loads((self.root / p).read_text())
        for value in ('2026-10-01', 'tomorrow', None, '2026-02-30'):
            self.f.put(p, {**original, 'checkedAt': value})
            self.assertEqual(self.project()['catalog']['standards'], [])

    def test_missing_evidence_and_private_text_excluded(self):
        (self.root / 'evidence/E_TEST.json').unlink()
        self.assertEqual(self.project()['catalog']['standards'], [])
        self.assertTrue(any('DEPENDENCY_MISSING' in x for x in validator.validate_namespace(self.root)['errors']))
        self.f.put('evidence/E_TEST.json', {'id': 'E_TEST'})
        self.f.clause['quote'] = '1 Local /workspace/private/report.pdf'
        self.f.entity('clauses', self.f.clause)
        self.config['standards'][0]['clauses'][0]['contentHash'] = content_hash(self.f.clause)
        self.save()
        self.assertEqual(self.project()['catalog']['standards'], [])

    def test_url_cannot_hide_private_path_or_multiline_prose(self):
        for value in ('https://example.gov.cn/file?path=/workspace/private/report.pdf',
                      'https://example.gov.cn/\n/home/private/file',
                      'https://name:secret@example.gov.cn/'):
            self.assertFalse(major._safe_public(value))
        self.assertTrue(major._safe_public('https://example.gov.cn/standard.pdf'))

    def test_keyword_title_and_fake_standard_never_expand_allowlist(self):
        original = self.project()
        self.f.put('law-versions/FAKE.json', {**self.f.version, 'id': 'FAKE', 'officialName': '重大事故隐患判定标准'})
        self.f.put('clauses/FAKE_C.json', {**self.f.clause, 'id': 'FAKE_C', 'lawVersionId': 'FAKE'})
        self.f.put('hazards/FAKE_H.json', {**self.f.hazard, 'id': 'FAKE_H', 'title': '重大事故隐患判定标准全覆盖'})
        self.assertEqual(original, self.project())
        self.f.law['canonicalName'] = 'Forged standard identity'
        self.f.entity('laws', self.f.law)
        self.assertEqual(self.project()['catalog']['standards'], [])

    def test_supporting_fallback_unapproved_links_never_become_topic(self):
        for role in ('supporting', 'fallback', 'direct'):
            self.f.link['role'] = role
            self.f.entity('links', self.f.link)
            self.config = synthetic_config(self.f)
            self.save()
            if role == 'direct':
                (self.root / 'reviews/links/K_TEST.json').unlink()
            self.assertEqual(self.project()['topic']['hazardIds'], [])
            self.assertEqual(len(self.standard()['clauses']), 1)

    def test_conditions_and_association_changes_invalidate_exact_topic_pin(self):
        self.f.hazard['conditions'] = 'New different subject condition'
        self.f.entity('hazards', self.f.hazard)
        self.f.entity('links', self.f.link)
        self.assertEqual(self.project()['topic']['hazardIds'], [])
        self.assertEqual(self.standard()['coverage']['reviewedClauseCount'], 1)

    def test_unknown_scope_keeps_counts_unknown_and_whole_distinct(self):
        s = self.config['standards'][0]
        s['scopeVerified'] = False
        s['expectedJudgmentItemCount'] = None
        s['clauses'][0]['judgmentItemCount'] = None
        s['clauses'][0]['granularity'] = 'subitem'
        self.save()
        c = self.standard()['coverage']
        self.assertEqual(c['status'], 'partial')
        self.assertIsNone(c['reviewedJudgmentItemCount'])
        self.assertEqual((c['reviewedWholeClauseCount'], c['reviewedSubitemClauseCount']), (0, 1))

    def test_pending_links_cannot_publish_and_expose_only_bounded_counts(self):
        s = self.config['standards'][0]
        a = s['topicLinks'].pop()
        s['pendingTopicLinks'] = [{k: a[k] for k in ('linkId', 'hazardId', 'clauseId')}]
        self.save()
        result = self.project()
        self.assertEqual(result['topic']['associations'], [])
        self.assertEqual(result['topic']['coverage']['excludedHazardCount'], 1)
        self.assertNotIn('pendingTopicLinks', json.dumps(result['topic']))

    def test_strict_schema_duplicate_identity_and_source_snapshot(self):
        self.assertIn('major-criteria/v1', release_snapshot.FORMAL_NAMESPACES)
        self.assertIn(major.CONFIG_PATH, release_snapshot.source_hashes(self.root))
        self.assertIn(('check_major_criteria', 'check_major_criteria.py'), validate_all.STEPS)
        self.assertIn('check_major_criteria', validate_all.BLOCKING)
        self.assertEqual(validator.validate_namespace(self.root)['errors'], [])
        self.config['standards'].append(copy.deepcopy(self.config['standards'][0])); self.save()
        with self.assertRaisesRegex(ValueError, 'MAJOR_STANDARD_ID'):
            self.project()
        self.config['standards'].pop(); self.save()
        self.f.put('clauses/duplicate.json', self.f.clause)
        with self.assertRaisesRegex(ValueError, 'duplicate identity'):
            self.project()

    def test_absent_configuration_is_empty_not_auto_discovered(self):
        (self.root / major.CONFIG_PATH).unlink()
        result = self.project()
        self.assertEqual(result['catalog']['standards'], [])
        self.assertEqual(result['topic']['associations'], [])
        self.assertEqual(validator.validate_namespace(self.root)['errors'], [])


class MajorCriteriaReleaseTests(unittest.TestCase):
    """Reuse the harness methods without rediscovering its unrelated tests."""
    fixture_type = fixtures.FieldProfileTests
    build = release_fixtures.FieldProfileReleaseTests.build
    read = release_fixtures.FieldProfileReleaseTests.read
    reseal = release_fixtures.FieldProfileReleaseTests.reseal
    verify = release_fixtures.FieldProfileReleaseTests.verify

    def setUp(self):
        release_fixtures.FieldProfileReleaseTests.setUp(self)
        self.config = synthetic_config(self.fixture)
        self.fixture.put(major.CONFIG_PATH, self.config)
        self.fixture.approve_synthetic()

    def test_major_bundle_exact_projection_and_legacy_payload_preserved(self):
        self.build()
        expected = major.public_projection(self.root, as_of=date(2026, 9, 30))
        for key, path in [('catalog', major.CATALOG_FILE), ('topic', major.TOPIC_FILE)]:
            self.assertEqual(self.read(path), expected[key])
            self.assertIn(path, self.read('site-manifest.json')['fileHashes'])
            self.assertIn(path, self.read('checksums.json'))
        rc, report = self.verify(); self.assertEqual(rc, 0, report)
        prior = {rel: (self.out / rel).read_bytes() for rel in ('data/search-index.json', 'data/law-index.json', 'data/field-profiles.json', 'data/hazards/h0000.json', 'data/clauses/c0000.json')}
        (self.root / major.CONFIG_PATH).unlink()
        self.build()
        for path, content in prior.items():
            self.assertEqual((self.out / path).read_bytes(), content, path)
        rc, report = self.verify(); self.assertEqual(rc, 0, report)

    def test_major_resealed_tampering_and_private_inventory_are_rejected(self):
        self.build()
        base = self.read(major.CATALOG_FILE)
        for key, value in [('quote', 'A different rule'), ('granularity', 'subitem'), ('sourceUrl', 'https://evil.example/fake')]:
            altered = copy.deepcopy(base)
            altered['standards'][0]['clauses'][0][key] = value
            (self.out / major.CATALOG_FILE).write_text(json.dumps(altered))
            self.reseal()
            rc, report = self.verify()
            self.assertEqual(rc, 1, report)
            self.assertTrue(any('重大判定精确公开投影' in error for error in report['errors']), report)
        (self.out / major.CATALOG_FILE).write_text(json.dumps(base))
        (self.out / 'data/major-private-inventory.json').write_text('{}')
        self.reseal()
        rc, report = self.verify(); self.assertEqual(rc, 1, report)
        self.assertTrue(any('白名单' in error for error in report['errors']))

    def test_major_configuration_changes_invalidate_snapshot_even_if_output_matches(self):
        self.build()
        (self.root / major.CONFIG_PATH).write_text(json.dumps(self.config, indent=2))
        expected = major.public_projection(self.root, as_of=date(2026, 9, 30))
        self.assertEqual(expected['catalog'], self.read(major.CATALOG_FILE))
        self.assertEqual(expected['topic'], self.read(major.TOPIC_FILE))
        rc, report = self.verify(); self.assertEqual(rc, 1, report)
        self.assertTrue(any('快照' in error for error in report['errors']), report)

    def test_major_resealed_topic_role_identity_and_warning_counts_are_rejected(self):
        self.build()
        base = self.read(major.TOPIC_FILE)
        variants = []
        for key, value in [('role', 'supporting'), ('hazardId', 'H_FAKE'), ('linkId', 'K_FAKE')]:
            altered = copy.deepcopy(base)
            altered['associations'][0][key] = value
            variants.append(altered)
        altered = copy.deepcopy(base)
        altered['coverage']['excludedHazardCount'] = 999
        variants.append(altered)
        for altered in variants:
            (self.out / major.TOPIC_FILE).write_text(json.dumps(altered))
            self.reseal()
            rc, report = self.verify(); self.assertEqual(rc, 1, report)
            self.assertTrue(any('重大判定精确公开投影' in error for error in report['errors']), report)


if __name__ == '__main__':
    unittest.main()
