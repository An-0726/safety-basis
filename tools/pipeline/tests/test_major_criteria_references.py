"""Synthetic-only checks: no real source approvals are created by tests."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4'))
from canonical import content_hash
import major_criteria_references as refs
import check_major_criteria_references as validator
import release_snapshot
import validate_all
import test_field_profiles as fixtures


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.FieldProfileTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.root
        self.pub = self.root / 'publication'
        self.f.version.update(documentNumber='SYN 1-2026', sourceUrl='https://example.gov.cn/standard', endDate=None)
        self.f.entity('law-versions', self.f.version)
        for kind, ident in [('laws', 'LF_TEST'), ('law-versions', 'LV_TEST')]:
            path = f'reviews/{kind}/{ident}.json'
            self.f.put(path, {**refs.read(self.root / path), 'checkedAt': '2026-10-01T08:00:00+00:00'})
        self.f.put('evidence/E_TEST.json', {'id': 'E_TEST', 'tier': 'authoritative-public',
                   'url': 'https://example.gov.cn/standard.pdf', 'snapshotSha256': 'a' * 64})
        self.record = {'schemaVersion': 1, 'id': 'REF_TEST', 'lawVersionId': 'LV_TEST', 'contentKind': 'reference_only',
                       'officialLink': self.f.version['sourceUrl'], 'officialTextLink': 'https://example.gov.cn/standard.pdf',
                       'searchTopics': [{'article': '5.1.1', 'searchTopic': '测试主题'}]}
        self.doc = {'lawId': 'LF_TEST', 'versionId': 'LV_TEST', 'title': 'Synthetic standard SYN 1-2026',
                    'version': 'synthetic', 'officialUrl': self.record['officialLink'], 'effectiveDate': '2020-01-01',
                    'status': '现行有效', 'textMode': 'link_only', 'fullTextSha256': '', 'textPath': None,
                    'fullTextReviewed': False, 'publicationPermission': 'metadata_only', 'validityNote': 'Synthetic metadata'}
        self.source_row = {'id': 'LV_TEST', 'sourceUrl': self.record['officialLink'], 'effectiveDate': '2020-01-01',
                           'documentNumber': 'SYN 1-2026', 'name': self.doc['title'], 'status': '现行有效',
                           'clauseRefs': [], 'hazardCount': 0}
        self.save_publication()
        self.save_record()
        self.approve_synthetic()

    def save_publication(self):
        self.f.put('publication/law-index.json', [self.source_row])
        self.f.put('publication/fulltext/catalog.json', {'documents': [self.doc]})
        self.f.put('publication/fulltext/search-index.json', {'documents': [{k: self.doc[k] for k in refs.SEARCH_FIELDS}]})

    def save_record(self):
        self.f.put(f'{refs.NAMESPACE}/records/REF_TEST.json', self.record)

    def approve_synthetic(self):
        self.review = {'schemaVersion': 1, 'referenceId': 'REF_TEST', 'decision': 'verified',
                       'checkedAt': '2026-10-01T12:00:00+08:00', 'reviewScope': refs.REVIEW_SCOPE,
                       'fullQuotePublicationReady': False, 'reviewer': 'Synthetic fixture only',
                       'reason': 'Synthetic metadata and short-topic test; not production approval',
                       **refs.review_bindings(self.record, self.root, self.pub)}
        self.save_review()

    def save_review(self):
        self.f.put(f'{refs.NAMESPACE}/reviews/REF_TEST.json', self.review)

    def project(self, at=date(2026, 10, 1)):
        return refs.public_projection(self.root, self.pub, as_of=at)

    def entries(self, at=date(2026, 10, 1)):
        return self.project(at)['public']['referenceEntries']

    def test_reference_without_h_k_or_c(self):
        for rel in ('hazards/H_TEST.json', 'links/K_TEST.json', 'clauses/C_TEST.json'):
            (self.root / rel).unlink()
        before = release_snapshot.source_hashes(self.root)
        entry = self.entries()[0]
        self.assertEqual(entry['searchTopicCount'], 1)
        self.assertEqual(entry['reviewedClauseCount'], 0)
        self.assertEqual(entry['directHazardCount'], 0)
        self.assertEqual(entry['publicationReady'], {'metadata': True, 'searchTopics': True, 'fullText': False})
        for key in ('quote', 'clauses', 'hazardIds', 'links', 'reviewer', 'dependencyFingerprint'):
            self.assertNotIn(key, entry)
        self.assertFalse(entry['fullTextReviewed'])
        self.assertFalse(entry['standaloneDeterminationAllowed'])
        self.assertFalse(self.project()['public']['allIndustryCoverage'])
        self.assertEqual(before, release_snapshot.source_hashes(self.root))

    def test_explicit_zero_topic_metadata_and_internal_spaces(self):
        self.record['searchTopics'][0]['searchTopic'] = '测试 主题'
        self.save_record(); self.approve_synthetic()
        self.assertEqual(self.entries()[0]['searchTopics'][0]['searchTopic'], '测试 主题')
        self.record['searchTopics'] = []
        self.save_record(); self.approve_synthetic()
        self.assertEqual(self.entries()[0]['searchTopicCount'], 0)
        self.assertEqual(self.entries()[0]['reviewedClauseCount'], 0)

    def test_real_review_date_not_backdated_to_law_date(self):
        self.assertEqual(self.entries(date(2026, 9, 30)), [])
        self.assertEqual(len(self.entries()), 1)
        self.assertEqual(self.entries(date(2019, 12, 31)), [])
        self.review['checkedAt'] = 'tomorrow'
        self.save_review()
        self.assertEqual(self.entries(), [])

    def test_missing_unreviewed_and_stale_record_review(self):
        p = self.root / refs.NAMESPACE / 'reviews/REF_TEST.json'
        for key, value in [('decision', 'proposed'), ('decision', 'rejected'), ('reviewedContentHash', '0' * 64),
                           ('dependencyFingerprint', '0' * 64), ('reviewScope', 'full_text'), ('checkedAt', '2026-10-01T08:00:00'),
                           ('fullQuotePublicationReady', True), ('checkedAt', None)]:
            original = copy.deepcopy(self.review)
            self.review[key] = value
            self.save_review()
            self.assertEqual(self.entries(), [], key)
            self.review = original
        p.unlink()
        self.assertEqual(self.entries(), [])

    def test_short_topics_require_distinct_exact_review(self):
        self.record['searchTopics'][0]['searchTopic'] = '另一主题'
        self.save_record()
        self.assertEqual(self.entries(), [])
        self.approve_synthetic()
        self.assertEqual(self.entries()[0]['searchTopics'][0]['searchTopic'], '另一主题')

    def test_identity_and_evidence_changes_invalidate_binding(self):
        for rel, key, value in [('laws/LF_TEST.json', 'canonicalName', 'Other name'),
                                ('evidence/E_TEST.json', 'snapshotSha256', 'b' * 64),
                                ('reviews/law-versions/LV_TEST.json', 'checkedAt', '2026-10-02')]:
            p = self.root / rel
            original = json.loads(p.read_text())
            self.f.put(rel, {**original, key: value})
            self.assertEqual(self.entries(), [])
            self.f.put(rel, original)

    def test_missing_evidence_and_formal_review(self):
        p = self.root / 'evidence/E_TEST.json'
        original = p.read_text()
        p.unlink()
        self.assertEqual(self.entries(), [])
        self.assertTrue(validator.validate_namespace(self.root, self.pub)['errors'])
        p.write_text(original)
        (self.root / 'reviews/laws/LF_TEST.json').unlink()
        self.assertEqual(self.entries(), [])

    def test_expired_upcoming_malformed_versions(self):
        for changes in ({'endDate': '2026-10-01'}, {'endDate': 'garbage'}, {'endDate': False},
                        {'validityStatus': 'upcoming'}, {'effectiveDate': '2027-01-01'}):
            original = copy.deepcopy(self.f.version)
            self.f.version.update(changes)
            self.f.entity('law-versions', self.f.version)
            self.approve_synthetic()
            self.assertEqual(self.entries(), [])
            self.f.version = original

    def test_reference_record_forbids_quote_full_conditions_and_unsafe_url(self):
        variants = [{**self.record, 'quote': 'Wrong full text'}, {**self.record, 'clauses': []},
                    {**self.record, 'officialLink': 'https://evil.example/standard'},
                    {**self.record, 'officialLink': 'https://u:p@example.gov.cn/standard'},
                    {**self.record, 'officialLink': 'https://example.gov.cn:444/standard'},
                    {**self.record, 'officialLink': 'https://example.gov.cn/\\standard'},
                    {**self.record, 'officialLink': 'https://example.gov.cn/%0aprivate'}]
        for value in ['中文' * 9, '完整条件。', '多行\n主题', '', ' topic', '/home/private', '人数>6']:
            variants.append({**self.record, 'searchTopics': [{'article': '5.1.1', 'searchTopic': value}]})
        for variant in variants:
            with self.assertRaises(ValueError):
                refs.validate_record(variant)

    def test_duplicate_article_and_non_string_topic_fail(self):
        for topics in ([self.record['searchTopics'][0]] * 2,
                       [{'article': '5.1.1', 'searchTopic': False}],
                       [{'article': '5.1.1', 'searchTopic': '主题', 'quote': 'text'}]):
            with self.assertRaises(ValueError):
                refs.validate_record({**self.record, 'searchTopics': topics})

    def test_unlisted_keyword_standard_is_not_discovered(self):
        before = self.project()
        self.f.put('law-versions/FAKE.json', {**self.f.version, 'id': 'FAKE', 'officialName': '重大事故隐患判定'})
        self.assertEqual(before, self.project())

    def test_link_only_cannot_smuggle_text_via_legacy_copy(self):
        for key, value in [('quote', 'secret'), ('textMode', 'full_text'), ('textPath', 'texts/private.json'),
                           ('fullTextReviewed', True), ('fullTextSha256', 'a' * 64),
                           ('publicationPermission', 'official_legal_text'), ('validityNote', '/workspace/private/file')]:
            original = copy.deepcopy(self.doc)
            self.doc[key] = value
            self.save_publication()
            with self.assertRaises(ValueError):
                self.project()
            self.doc = original

    def test_search_metadata_cannot_smuggle_additional_fields(self):
        path = 'publication/fulltext/search-index.json'
        value = refs.read(self.root / path)
        value['documents'][0]['quote'] = 'private original'
        self.f.put(path, value)
        with self.assertRaisesRegex(ValueError, 'REFERENCE_FULLTEXT_SEARCH_METADATA'):
            self.project()

    def test_inconsistent_metadata_cannot_be_fixed_just_by_resigning(self):
        for key, value in [('title', 'Other standard'), ('version', '2099'), ('status', '已废止')]:
            original = copy.deepcopy(self.doc)
            self.doc[key] = value
            self.save_publication()
            self.approve_synthetic()
            self.assertEqual(self.entries(), [])
            self.doc = original

    def test_missing_metadata_review_date_is_not_legacy_approved(self):
        path = 'reviews/laws/LF_TEST.json'
        value = refs.read(self.root / path)
        value.pop('checkedAt')
        self.f.put(path, value)
        self.approve_synthetic()
        self.assertEqual(self.entries(), [])

    def test_source_metadata_change_requires_new_scope_review(self):
        self.doc['validityNote'] = 'Changed metadata'
        self.save_publication()
        self.assertEqual(self.entries(), [])

    def test_filtered_library_preserves_legacy_rows_and_non_documents(self):
        legacy = {'versionId': 'UNRELATED', 'textMode': 'full_text'}
        payload = {'documents': [legacy, self.doc], 'gramShards': {'abc': 'unchanged'}}
        old = refs.project_publication(payload, self.project(date(2026, 9, 30)))
        self.assertEqual(old, {'documents': [legacy], 'gramShards': {'abc': 'unchanged'}, 'asOf': '2026-09-30'})
        self.assertEqual(refs.project_publication(payload, self.project()), {**payload, 'asOf': '2026-10-01'})
        self.assertEqual(len(payload['documents']), 2)

    def test_snapshot_and_blocking_validator_cover_reference_namespace(self):
        self.assertIn(refs.NAMESPACE, release_snapshot.FORMAL_NAMESPACES)
        self.assertIn('check_major_criteria_references', validate_all.BLOCKING)
        self.assertEqual(validator.validate_namespace(self.root, self.pub)['errors'], [])
        before = release_snapshot.snapshot_digest(release_snapshot.source_hashes(self.root))
        p = self.root / refs.NAMESPACE / 'records/REF_TEST.json'
        p.write_text(p.read_text() + '\n')
        after = release_snapshot.snapshot_digest(release_snapshot.source_hashes(self.root))
        self.assertNotEqual(before, after)

    def test_no_implicit_today(self):
        with self.assertRaises(TypeError):
            refs.public_projection(self.root, self.pub)
        with self.assertRaises(TypeError):
            refs.public_projection(self.root, self.pub, as_of='2026-10-01')


class ReferenceReleaseTests(unittest.TestCase):
    def setUp(self):
        from test_field_profile_release import FieldProfileReleaseTests
        self.fixture_holder = ReferenceTests()
        self.fixture_holder.setUp()
        self.addCleanup(self.fixture_holder.doCleanups)
        f = self.fixture_holder
        self.fixture = f.f
        self.root, self.publication = f.root, f.pub
        self.fixture.law['documentKind'] = '法律'
        self.fixture.entity('laws', self.fixture.law)
        law_review_path = 'reviews/laws/LF_TEST.json'
        self.fixture.put(law_review_path, {**refs.read(self.root / law_review_path), 'checkedAt': '2026-10-01T08:00:00+00:00'})
        self.fixture.hazard.update(note='', mode='direct', conditions='Synthetic exact source condition')
        self.fixture.entity('hazards', self.fixture.hazard)
        self.fixture.entity('links', self.fixture.link)
        self.fixture.approve_synthetic()
        f.approve_synthetic()
        self.fixture.put('manifest.json', {'synthetic': True})
        self.out = self.root / 'source/releases/test'
        self.selection = self.root / 'selection.json'
        doc = {'versionId': 'LV_STD_GBT47236_2026', 'textMode': 'link_only',
               'officialUrl': 'https://openstd.samr.gov.cn/', 'effectiveDate': '2026-09-01'}
        for rel, extra in [('law-index.json', {'id': 'LV_STD_GBT47236_2026'}),
                           ('fulltext/catalog.json', doc), ('fulltext/search-index.json', doc)]:
            path = self.publication / rel
            payload = refs.read(path)
            (payload if isinstance(payload, list) else payload['documents']).append(extra)
            self.fixture.put('publication/' + rel, payload)
        # Adding unrelated metadata does not alter this exact record's review binding.
        self.assertEqual(len(f.entries()), 1)

    from test_field_profile_release import FieldProfileReleaseTests as _Harness
    build = _Harness.build
    read = _Harness.read
    reseal = _Harness.reseal
    verify = _Harness.verify

    def test_bundle_and_historical_library_are_exact_without_changing_hazards(self):
        self.build('2026-10-01')
        manifest = self.read('data/manifest.json')
        self.assertEqual(manifest['files']['majorCriteriaReferences'], refs.REFERENCE_FILE)
        self.assertEqual(manifest['counts']['majorCriteriaReferenceStandards'], 1)
        self.assertEqual(manifest['counts']['majorCriteriaSearchTopics'], 1)
        self.assertIn(refs.REFERENCE_FILE, self.read('site-manifest.json')['fileHashes'])
        self.assertIn(refs.REFERENCE_FILE, self.read('checksums.json'))
        rc, report = self.verify(); self.assertEqual(rc, 0, report)
        before = {path: (self.out / path).read_bytes() for path in
                  ('data/search-index.json', 'data/law-index.json', 'data/hazards/h0000.json', 'data/clauses/c0000.json')}
        self.build('2026-09-30')
        self.assertEqual(self.read(refs.REFERENCE_FILE)['referenceEntries'], [])
        for name in ('catalog.json', 'search-index.json'):
            payload = self.read('data/fulltext/' + name)
            self.assertNotIn('LV_TEST', [e['versionId'] for e in payload['documents']])
            self.assertEqual(payload['asOf'], '2026-09-30')
        for path, value in before.items():
            self.assertEqual((self.out / path).read_bytes(), value, path)
        rc, report = self.verify(); self.assertEqual(rc, 0, report)

    def test_resealed_reference_text_and_false_counts_are_rejected(self):
        self.build('2026-10-01')
        base = self.read(refs.REFERENCE_FILE)
        variants = []
        for key, value in [('quote', 'Private complete condition'), ('fullTextReviewed', True),
                           ('reviewedClauseCount', 53), ('directHazardCount', 53), ('standaloneDeterminationAllowed', True)]:
            payload = copy.deepcopy(base)
            payload['referenceEntries'][0][key] = value
            variants.append(payload)
        payload = copy.deepcopy(base)
        payload['referenceEntries'][0]['searchTopics'][0]['searchTopic'] = 'Changed topic'
        variants.append(payload)
        for payload in variants:
            (self.out / refs.REFERENCE_FILE).write_text(json.dumps(payload))
            self.reseal()
            rc, report = self.verify()
            self.assertEqual(rc, 1, report)
            self.assertTrue(any('官方查阅入口精确投影' in e for e in report['errors']), report)
            self.assertFalse(any('Hash' in e or '哈希' in e for e in report['errors']), report)

    def test_resealed_unreviewed_legacy_library_entry_is_rejected(self):
        self.build('2026-09-30')
        for name in ('catalog.json', 'search-index.json'):
            path = self.out / 'data/fulltext' / name
            payload = refs.read(path)
            payload['documents'].append(self.fixture_holder.doc)
            path.write_text(json.dumps(payload))
        self.reseal()
        rc, report = self.verify()
        self.assertEqual(rc, 1, report)
        self.assertTrue(any('受控日期投影' in e for e in report['errors']), report)

    def test_changed_record_bytes_invalidate_source_snapshot(self):
        self.build('2026-10-01')
        path = self.root / refs.NAMESPACE / 'records/REF_TEST.json'
        path.write_text(path.read_text() + '\n')
        rc, report = self.verify()
        self.assertEqual(rc, 1, report)
        self.assertTrue(any('快照' in e for e in report['errors']), report)


if __name__ == '__main__':
    unittest.main()
