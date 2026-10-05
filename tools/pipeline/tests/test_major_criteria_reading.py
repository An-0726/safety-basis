"""Independent reading-only Gate QA; approvals are synthetic and temporary only.

The production regression class only reads checked-in records and reviews. No
test signs or repairs a production review, and no source publication is changed.
"""
import copy
from datetime import date, datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
import major_criteria as major
import major_criteria_directory as directory
import major_criteria_reading as reading
from release_gate_core import evaluate_release_gate
import release_snapshot
import validate_all
import test_major_criteria_directory as directory_fixtures
import test_field_profile_release as release_fixtures

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    Draft202012Validator = None

AS_OF = date(2026, 10, 1)
SCHEMA_PATH = ROOT / 'tools/v4/schemas/major-criteria-reading.schema.json'


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.d = directory_fixtures.DirectoryTests()
        self.d.setUp()
        self.addCleanup(self.d.doCleanups)
        self.fixture = self.d.f.f
        self.root, self.pub = self.d.root, self.d.pub
        self.companion = self.d.companion()
        # The primary has a known date; only the supplement's date is unknown.
        version = reading.read(self.root / 'law-versions/LV_COMP.json')
        version['effectiveDate'] = None
        self.d.entity('law-versions', version)
        for rel in ('law-index.json', 'fulltext/catalog.json'):
            data = reading.read(self.pub / rel)
            rows = data if isinstance(data, list) else data['documents']
            for row in rows:
                if row.get('versionId', row.get('id')) == 'LV_COMP':
                    row.update(effectiveDate=None, status='现行使用中')
            self.put('publication/' + rel, data)
        self.companion.update(referenceStatus='current_in_use',
                              effectiveDateNote='Synthetic: no explicit effective date; never infer one')
        self.d.save_record(self.companion)
        self.d.approve()
        self.d.approve(self.companion)
        entries = {e['id']: e for e in self.d.entries()}
        self.assertEqual(set(entries), {'DIR_TEST', 'DIR_COMP'})
        self.record = {
            'schemaVersion': 1, 'id': 'READING_SYNTHETIC', 'directoryGroupId': 'test_group',
            'primaryReferenceId': 'DIR_TEST', 'requiredReferenceIds': ['DIR_TEST', 'DIR_COMP'],
            'readingReason': 'effective_date_not_fully_verified',
            'warning': 'Synthetic official reading only; no current determination eligibility',
            'documents': [], 'evidence': {},
            'publication': {'basis': reading.BASIS, 'legalSourceUrl': 'https://example.gov.cn/copyright',
                            'evidenceIds': ['E_RIGHTS_SYNTHETIC']},
        }
        for reference_id, item_count, note_count in [('DIR_TEST', 64, 13), ('DIR_COMP', 8, 4)]:
            entry = entries[reference_id]
            evidence_id = 'E_BODY_' + reference_id
            use_id = 'E_USE_' + reference_id
            note_id = 'E_NOTE_' + reference_id
            body_url = entry['officialTextLink']
            use_url = 'https://example.gov.cn/current-use/' + reference_id
            note_url = 'https://example.gov.cn/explanation/' + reference_id
            for eid, url in [(evidence_id, body_url), (use_id, use_url), (note_id, note_url)]:
                self.record['evidence'][eid] = {
                    'id': eid, 'url': url, 'tier': 'authoritative-public', 'snapshotSha256': 'a' * 64,
                    'snapshotKind': 'synthetic fixture text only', 'locator': 'Synthetic full source',
                    'sourceDate': '2026-09-29', 'retrievedAt': '2026-10-01',
                }
            item_rows = [{'id': reference_id + '_ITEM_' + str(i), 'articleLabel': 'Item ' + str(i),
                          'quote': 'Synthetic condition ' + str(i) + '; synthetic explicit exception retained.'}
                         for i in range(1, item_count + 1)]
            notes = []
            for i in range(note_count):
                notes.append({
                    'id': reference_id + '_NOTE_' + str(i), 'appliesToItemIds': [item_rows[i % item_count]['id']],
                    'textMode': 'official_link_pending' if reference_id == 'DIR_COMP' and i == 3 else 'reviewed_summary',
                    'text': 'Synthetic explanation including the stated exception; pending links are not quotes.',
                    'sourceDate': '2026-09-29', 'sourceUrl': note_url, 'sourcePages': [1, 2], 'evidenceId': note_id,
                })
            self.record['documents'].append({
                'directoryReferenceId': reference_id, 'sourceIdentity': reading.source_identity(entry),
                'noticeText': 'Synthetic notice and all synthetic introductory text.',
                'sections': [{'id': reference_id + '_SECTION', 'title': 'Synthetic section', 'items': item_rows}],
                'firstLevelItemCount': item_count, 'sourceEvidenceIds': [evidence_id],
                'currentUseEvidence': [{'sourceDate': '2026-09-29', 'sourceUrl': use_url,
                                        'summary': 'Synthetic evidence of current use, not a start date.', 'evidenceId': use_id}],
                'officialClarifications': notes,
            })
        self.put('evidence/E_RIGHTS_SYNTHETIC.json', {
            'id': 'E_RIGHTS_SYNTHETIC', 'tier': 'authoritative-public',
            'url': self.record['publication']['legalSourceUrl'], 'snapshotSha256': 'c' * 64,
            'locator': 'Synthetic Article 5 permission evidence', 'retrievedAt': '2026-10-01',
        })
        self.save_record()
        self.approve_texts()
        self.approve_scope()

    def put(self, rel, value):
        self.fixture.put(rel, value)

    def save_record(self):
        self.put(f'{reading.NAMESPACE}/records/{self.record["id"]}.json', self.record)

    def approve_texts(self):
        for doc in self.record['documents']:
            binding = reading.text_review_binding(doc)
            review = {
                'schemaVersion': 1, 'directoryReferenceId': doc['directoryReferenceId'], 'decision': 'verified',
                'reviewScope': reading.TEXT_SCOPE, 'reviewedContentHash': binding['reviewedContentHash'],
                'itemDecisions': [{**row, 'decision': 'verified'} for row in binding['itemContentHashes']],
                'checkedAt': '2026-10-01T10:00:00+00:00', 'reviewer': 'Synthetic temporary fixture only',
                'reason': 'Synthetic body and every synthetic first-level item; not an actual legal review',
            }
            self.put(f'{reading.NAMESPACE}/text-reviews/{doc["directoryReferenceId"]}.json', review)

    def approve_scope(self):
        review = {
            'schemaVersion': 1, 'readingGroupId': self.record['id'], 'decision': 'verified',
            'reviewScope': reading.SCOPE, 'checkedAt': '2026-10-01T11:00:00+00:00',
            'referenceTextPublicationReady': True, 'currentDeterminationBasis': False,
            'reviewer': 'Independent synthetic temporary fixture only',
            'reason': 'Synthetic exact identity, evidence, rights, notes, and unknown-date boundary only',
            **reading.review_bindings(self.record, self.root, self.pub),
        }
        self.put(f'{reading.NAMESPACE}/scope-reviews/{self.record["id"]}.json', review)

    def project(self, at=AS_OF):
        return reading.public_projection(self.root, self.pub, as_of=at)

    def assert_blocked(self, reason=None):
        result = self.project()
        public = result['public']
        self.assertEqual(public['readingGroups'], [])
        self.assertEqual((public['readingGroupCount'], public['sourceDocumentCount'], public['firstLevelItemCount']), (0, 0, 0))
        if reason:
            self.assertIn(reason, [row['reason'] for row in result['inventory']['excluded']])

    def test_reviewed_group_is_one_group_two_documents_72_items_without_current_eligibility(self):
        before = release_snapshot.source_hashes(self.root)
        gate_before = evaluate_release_gate(self.root, AS_OF)
        public = self.project()['public']
        self.assertEqual((public['readingGroupCount'], public['sourceDocumentCount'], public['firstLevelItemCount']), (1, 2, 72))
        self.assertTrue(public['referenceOnly'])
        self.assertFalse(public['currentDeterminationBasis'])
        self.assertFalse(public['standaloneDeterminationAllowed'])
        self.assertFalse(public['allIndustryCoverage'])
        self.assertEqual((public['reviewedCurrentClauseCount'], public['directHazardCount']), (0, 0))
        docs = public['readingGroups'][0]['documents']
        self.assertEqual([d['firstLevelItemCount'] for d in docs], [64, 8])
        self.assertEqual([d['sourceIdentity']['effectiveDate'] for d in docs], ['2020-01-01', None])
        notes = [n for d in docs for n in d['officialClarifications']]
        self.assertEqual(sum(n['textMode'] == 'reviewed_summary' for n in notes), 16)
        self.assertEqual(sum(n['textMode'] == 'official_link_pending' for n in notes), 1)
        self.assertTrue(all(n['isOfficialNormText'] is False for n in notes))
        self.assertEqual(before, release_snapshot.source_hashes(self.root))
        gate_after = evaluate_release_gate(self.root, AS_OF)
        self.assertEqual(gate_before.eligible_hazards, gate_after.eligible_hazards)
        self.assertEqual(gate_before.eligible_links, gate_after.eligible_links)
        self.assertFalse(gate_after.law_versions['LV_COMP']['supports_current'])

    def test_as_of_boundary_requires_explicit_date_and_never_backdates_approvals(self):
        self.assertEqual(self.project(date(2026, 9, 30))['public']['readingGroups'], [])
        self.assertEqual(self.project()['public']['readingGroupCount'], 1)
        with self.assertRaises(TypeError):
            reading.public_projection(self.root, self.pub)
        for value in ['2026-10-01', None, datetime(2026, 10, 1)]:
            with self.subTest(value=value), self.assertRaises(TypeError):
                reading.public_projection(self.root, self.pub, as_of=value)

    def test_reading_does_not_require_or_recreate_any_c_h_k(self):
        for rel in ['clauses/C_TEST.json', 'hazards/H_TEST.json', 'links/K_TEST.json']:
            (self.root / rel).unlink()
        before = release_snapshot.source_hashes(self.root)
        self.assertEqual(self.project()['public']['readingGroupCount'], 1)
        self.assertEqual(before, release_snapshot.source_hashes(self.root))
        for namespace in ['clauses', 'hazards', 'links']:
            self.assertEqual(list((self.root / namespace).glob('*.json')), [])

    def test_missing_invalid_future_stale_text_reviews_hold_whole_group(self):
        for reference in self.record['requiredReferenceIds']:
            rel = f'{reading.NAMESPACE}/text-reviews/{reference}.json'
            original = reading.read(self.root / rel)
            changes = [
                {'decision': 'proposed'}, {'decision': 'rejected'}, {'checkedAt': '2026-10-02'},
                {'checkedAt': '2026-02-30'}, {'checkedAt': '2026-10-01T10:00:00'}, {'checkedAt': None},
                {'checkedAt': False}, {'reviewedContentHash': '0' * 64}, {'directoryReferenceId': 'OTHER'},
                {'reviewScope': reading.SCOPE}, {'reviewer': ''}, {'reason': ''}, {'schemaVersion': True},
                {'itemDecisions': original['itemDecisions'][:-1]}, {'itemDecisions': []},
                {'itemDecisions': list(reversed(original['itemDecisions']))}, {'extra': 'unreviewed'},
            ]
            for change in changes:
                with self.subTest(reference=reference, change=change):
                    self.put(rel, {**original, **change})
                    self.assert_blocked('TEXT_REVIEW_FAILED')
            for field, value in [('itemId', 'OTHER'), ('decision', 'proposed'), ('reviewedContentHash', '0' * 64)]:
                changed = copy.deepcopy(original)
                changed['itemDecisions'][0][field] = value
                self.put(rel, changed)
                self.assert_blocked('TEXT_REVIEW_FAILED')
            (self.root / rel).unlink()
            self.assert_blocked('DEPENDENCY_MISSING')
            self.put(rel, original)
        self.assertEqual(self.project()['public']['readingGroupCount'], 1)

    def test_missing_invalid_future_stale_scope_review_holds_whole_group(self):
        rel = f'{reading.NAMESPACE}/scope-reviews/{self.record["id"]}.json'
        original = reading.read(self.root / rel)
        for change in [
            {'decision': 'proposed'}, {'checkedAt': '2026-10-02'}, {'checkedAt': '2026-02-30'},
            {'checkedAt': '2026-10-01T11:00:00'}, {'checkedAt': None}, {'checkedAt': False},
            {'reviewedContentHash': '0' * 64}, {'dependencyFingerprint': '0' * 64},
            {'readingGroupId': 'OTHER'}, {'reviewScope': reading.TEXT_SCOPE}, {'reviewer': ''},
            {'reason': ''}, {'schemaVersion': True}, {'referenceTextPublicationReady': False},
            {'currentDeterminationBasis': True}, {'extra': 'unreviewed'},
        ]:
            with self.subTest(change=change):
                self.put(rel, {**original, **change})
                self.assert_blocked()
        (self.root / rel).unlink()
        self.assert_blocked('SCOPE_REVIEW_FAILED')

    def test_body_and_each_item_are_bound_even_after_scope_is_refreshed(self):
        original = copy.deepcopy(self.record)
        mutations = [
            lambda d: d.update(noticeText=d['noticeText'] + ' Changed'),
            lambda d: d['sections'][0].update(title='Changed heading'),
            lambda d: d['sections'][0]['items'][0].update(quote='Changed synthetic quotation'),
            lambda d: d['sections'][0]['items'][0].update(articleLabel='Changed item number'),
        ]
        for doc_index in (0, 1):
            for mutate in mutations:
                self.record = copy.deepcopy(original)
                mutate(self.record['documents'][doc_index])
                self.save_record()
                self.approve_scope()
                self.assert_blocked('TEXT_REVIEW_FAILED')

    def test_deleted_or_reordered_items_need_new_individual_text_approval(self):
        original = copy.deepcopy(self.record)
        for index in (0, 1):
            for remove in [False, True]:
                self.record = copy.deepcopy(original)
                doc = self.record['documents'][index]
                if remove:
                    doc['sections'][0]['items'].pop()
                    doc['firstLevelItemCount'] -= 1
                else:
                    doc['sections'][0]['items'].reverse()
                self.save_record()
                self.approve_scope()
                self.assert_blocked('TEXT_REVIEW_FAILED')

    def test_scope_review_cannot_precede_text_or_evidence_review_day(self):
        rel = f'{reading.NAMESPACE}/scope-reviews/{self.record["id"]}.json'
        original = reading.read(self.root / rel)
        self.put(rel, {**original, 'checkedAt': '2026-09-30'})
        self.assert_blocked('TEXT_REVIEW_AFTER_SCOPE')

    def test_unreviewed_warning_rights_and_explanation_removal_stale_the_group(self):
        original = copy.deepcopy(self.record)
        for mutate in [lambda r: r.update(warning='Changed warning'),
                       lambda r: r['publication'].update(legalSourceUrl='https://example.gov.cn/other-law'),
                       lambda r: r['documents'][0]['officialClarifications'].pop()]:
            self.record = copy.deepcopy(original)
            mutate(self.record)
            self.save_record()
            self.assert_blocked('REVIEW_BINDING_STALE')

    def test_note_exceptions_pending_links_and_current_use_are_bound_to_scope(self):
        original = copy.deepcopy(self.record)
        for field, value in [('text', 'Changed explanation dropping an exception'), ('textMode', 'official_link_pending'),
                             ('sourcePages', [3]), ('appliesToItemIds', ['DIR_TEST_ITEM_2'])]:
            self.record = copy.deepcopy(original)
            self.record['documents'][0]['officialClarifications'][0][field] = value
            self.save_record()
            self.assert_blocked('REVIEW_BINDING_STALE')
        self.record = copy.deepcopy(original)
        self.record['documents'][1]['officialClarifications'][-1]['textMode'] = 'reviewed_summary'
        self.save_record()
        self.assert_blocked('REVIEW_BINDING_STALE')
        self.record = copy.deepcopy(original)
        self.record['documents'][0]['currentUseEvidence'][0]['summary'] = 'Changed current-use assertion'
        self.save_record()
        self.assert_blocked('REVIEW_BINDING_STALE')

    def test_source_hash_and_complete_evidence_fields_are_bound(self):
        original = copy.deepcopy(self.record)
        for eid in original['evidence']:
            for key, value in [('snapshotSha256', 'e' * 64), ('locator', 'Changed locator'),
                               ('snapshotKind', 'Changed evidence material')]:
                self.record = copy.deepcopy(original)
                self.record['evidence'][eid][key] = value
                self.save_record()
                self.assert_blocked('REVIEW_BINDING_STALE')

    def test_metadata_and_all_independent_review_dependencies_are_bound(self):
        for rel, field, value in [
            ('laws/LF_COMP.json', 'issuer', 'Changed issuer'),
            ('law-versions/LV_COMP.json', 'documentNumber', 'Changed version'),
            ('evidence/E_TEST.json', 'snapshotSha256', 'd' * 64),
            ('reviews/laws/LF_COMP.json', 'checkedAt', '2026-10-02'),
            ('reviews/law-versions/LV_COMP.json', 'reviewedContentHash', '0' * 64),
            (f'{directory.NAMESPACE}/reviews/DIR_COMP.json', 'reason', 'Changed independently reviewed reason'),
            (f'{reading.NAMESPACE}/text-reviews/DIR_COMP.json', 'reason', 'Changed textual review reason'),
        ]:
            original = reading.read(self.root / rel)
            with self.subTest(rel=rel, field=field):
                self.put(rel, {**original, field: value})
                self.assert_blocked()
            self.put(rel, original)

    def test_missing_directory_or_metadata_reviews_block_entire_group(self):
        for rel in [f'{directory.NAMESPACE}/reviews/DIR_TEST.json', f'{directory.NAMESPACE}/reviews/DIR_COMP.json',
                    'reviews/laws/LF_COMP.json', 'reviews/law-versions/LV_COMP.json', 'evidence/E_TEST.json']:
            path = self.root / rel
            original = path.read_bytes()
            with self.subTest(rel=rel):
                path.unlink()
                self.assert_blocked()
            path.write_bytes(original)

    def test_required_main_or_supplement_cannot_be_dropped_from_record(self):
        for index in (0, 1):
            changed = copy.deepcopy(self.record)
            changed['documents'].pop(index)
            with self.assertRaisesRegex(ValueError, 'READING_REQUIRED_DOCUMENTS'):
                reading.validate_record(changed)
        for ident in ['DIR_TEST', 'DIR_COMP']:
            path = self.root / directory.NAMESPACE / 'records' / (ident + '.json')
            original = path.read_bytes()
            path.unlink()
            with self.subTest(ident=ident), self.assertRaises(ValueError):
                self.project()
            path.write_bytes(original)

    def test_future_current_use_and_note_evidence_stay_excluded_even_if_scope_resigned(self):
        original = copy.deepcopy(self.record)
        for key in ['currentUseEvidence', 'officialClarifications']:
            self.record = copy.deepcopy(original)
            row = self.record['documents'][0][key][0]
            evidence_id = row['evidenceId']
            # All notes sharing the evidence must retain the exact source date.
            for document in self.record['documents']:
                for r in document['currentUseEvidence'] + document['officialClarifications']:
                    if r['evidenceId'] == evidence_id:
                        r['sourceDate'] = '2026-10-02'
            self.record['evidence'][evidence_id].update(sourceDate='2026-10-02', retrievedAt='2026-10-02')
            self.save_record()
            self.approve_scope()
            self.assert_blocked('EVIDENCE_DATE_FAILED')

    def test_unknown_effective_date_never_infers_from_publication_or_use(self):
        before = copy.deepcopy(self.record)
        self.assertIsNone(self.project()['public']['readingGroups'][0]['documents'][1]['sourceIdentity']['effectiveDate'])
        self.assertEqual(self.record, before)
        self.assertIsNone(reading.read(self.root / 'law-versions/LV_COMP.json')['effectiveDate'])
        changed = copy.deepcopy(self.record)
        identity = changed['documents'][1]['sourceIdentity']
        identity['effectiveDate'] = identity['publicationDate']
        with self.assertRaisesRegex(ValueError, 'READING_UNKNOWN_DATE_REASON_REQUIRED'):
            reading.validate_record(changed)
        # Keep a different unknown date to exercise identity matching separately.
        changed['documents'][0]['sourceIdentity'].update(effectiveDate=None, effectiveDateNote='Synthetic unknown')
        self.record = changed
        self.save_record()
        self.approve_scope()
        self.assert_blocked('DIRECTORY_IDENTITY_CHANGED')

    def test_source_identity_is_exact_and_not_a_technical_standard(self):
        original = copy.deepcopy(self.record)
        for field in ['issuer', 'title', 'documentNumber', 'versionKey', 'legalNature', 'scopeHint', 'scopeCaveat']:
            self.record = copy.deepcopy(original)
            self.record['documents'][0]['sourceIdentity'][field] += ' changed'
            self.save_record()
            self.approve_scope()
            self.assert_blocked('DIRECTORY_IDENTITY_CHANGED')
        for value in ['国家标准', '强制性国家标准', 'GB技术标准', '行业标准', [], {}, None, False, 1]:
            changed = copy.deepcopy(original)
            changed['documents'][0]['sourceIdentity']['documentKind'] = value
            with self.subTest(kind=value), self.assertRaisesRegex(ValueError, 'READING_SOURCE_IDENTITY'):
                reading.validate_record(changed)

    def test_missing_rights_and_bad_rights_evidence_cannot_be_resigned_away(self):
        rel = 'evidence/E_RIGHTS_SYNTHETIC.json'
        original = reading.read(self.root / rel)
        for change in [{'tier': 'unverified'}, {'snapshotSha256': ''}, {'locator': ''},
                       {'url': 'https://example.gov.cn/different-law'}, {'url': 'https://evil.example/rights'},
                       {'retrievedAt': '2026-10-02'}, {'retrievedAt': 'invalid'}]:
            self.put(rel, {**original, **change})
            self.approve_scope()
            self.assert_blocked()
        (self.root / rel).unlink()
        self.approve_scope()
        self.assert_blocked('DEPENDENCY_MISSING')

    def test_bad_official_urls_are_rejected_in_every_source_location(self):
        setters = [lambda r, v: r['publication'].update(legalSourceUrl=v),
                   lambda r, v: r['documents'][0]['sourceIdentity'].update(officialLink=v),
                   lambda r, v: r['documents'][0]['sourceIdentity'].update(officialTextLink=v),
                   lambda r, v: r['documents'][0]['currentUseEvidence'][0].update(sourceUrl=v),
                   lambda r, v: r['documents'][0]['officialClarifications'][0].update(sourceUrl=v),
                   lambda r, v: r['evidence']['E_BODY_DIR_TEST'].update(url=v)]
        for url in ['http://example.gov.cn/source', 'https://evil.example/source', 'https://example.gov.cn.evil.example/',
                    'https://name:secret@example.gov.cn/', 'https://example.gov.cn:444/',
                    'https://example.gov.cn/\\private', 'https://example.gov.cn/%0aprivate',
                    'https://example.gov.cn/\nsource']:
            for setter in setters:
                changed = copy.deepcopy(self.record)
                setter(changed, url)
                with self.subTest(url=url), self.assertRaises(ValueError):
                    reading.validate_record(changed)

    def test_record_rejects_c_h_k_injection_and_count_mismatch(self):
        selectors = [lambda r: r, lambda r: r['documents'][0], lambda r: r['documents'][0]['sourceIdentity'],
                     lambda r: r['documents'][0]['sections'][0], lambda r: r['documents'][0]['sections'][0]['items'][0],
                     lambda r: r['documents'][0]['officialClarifications'][0], lambda r: r['publication']]
        for field in ['clauseId', 'hazardIds', 'basisLinkIds', 'clauses', 'hazards', 'links',
                      'currentDeterminationBasis', 'reviewedCurrentClauseCount', 'directHazardCount']:
            for select in selectors:
                changed = copy.deepcopy(self.record)
                select(changed)[field] = True
                with self.subTest(field=field), self.assertRaises(ValueError):
                    reading.validate_record(changed)
        for value in [0, 63, 65, True, '64']:
            changed = copy.deepcopy(self.record)
            changed['documents'][0]['firstLevelItemCount'] = value
            with self.subTest(count=value), self.assertRaisesRegex(ValueError, 'READING_ITEM_COUNT'):
                reading.validate_record(changed)

    def test_dates_have_no_model_or_machine_fallback(self):
        for value in [False, True, 0, '', '2026-1-1', '2026-02-30', '2026-10-01T00:00:00Z']:
            for field in ['effectiveDate', 'publicationDate']:
                changed = copy.deepcopy(self.record)
                changed['documents'][1]['sourceIdentity'][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    reading.validate_record(changed)
        changed = copy.deepcopy(self.record)
        changed['documents'][1]['sourceIdentity']['effectiveDateNote'] = ''
        with self.assertRaises(ValueError):
            reading.validate_record(changed)

    def test_output_bytes_are_deterministic_across_hash_seeds(self):
        code = ("import sys,json;from datetime import date;sys.path.insert(0,sys.argv[1]);"
                "from major_criteria_reading import public_projection;"
                "print(json.dumps(public_projection(sys.argv[2],sys.argv[3],as_of=date(2026,10,1))['public'],ensure_ascii=False))")
        args = [sys.executable, '-c', code, str(ROOT / 'tools/v4'), str(self.root), str(self.pub)]
        self.assertEqual(subprocess.check_output(args, env={**os.environ, 'PYTHONHASHSEED': '1'}),
                         subprocess.check_output(args, env={**os.environ, 'PYTHONHASHSEED': '7'}))

    @unittest.skipUnless(Draft202012Validator is not None, 'Optional jsonschema package is unavailable')
    def test_public_schema_whitelists_all_layers_constants_identity_dates_and_links(self):
        schema = reading.read(SCHEMA_PATH)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        public = self.project()['public']
        self.assertEqual(list(validator.iter_errors(public)), [])
        self.assertEqual(list(validator.iter_errors(self.project(date(2026, 9, 30))['public'])), [])
        self.assertEqual(set(schema['$defs']['sourceIdentity']['required']), reading.IDENTITY_FIELDS)
        selectors = [lambda r: r, lambda r: r['readingGroups'][0], lambda r: r['readingGroups'][0]['documents'][0],
                     lambda r: r['readingGroups'][0]['documents'][0]['sourceIdentity'],
                     lambda r: r['readingGroups'][0]['documents'][0]['sourceIdentity']['directoryGroup'],
                     lambda r: r['readingGroups'][0]['documents'][0]['sections'][0],
                     lambda r: r['readingGroups'][0]['documents'][0]['sections'][0]['items'][0],
                     lambda r: r['readingGroups'][0]['documents'][0]['officialClarifications'][0],
                     lambda r: r['readingGroups'][0]['documents'][0]['currentUseEvidence'][0],
                     lambda r: r['readingGroups'][0]['publicationBasis']]
        for select in selectors:
            for field in list(select(public)):
                changed = copy.deepcopy(public)
                del select(changed)[field]
                self.assertTrue(list(validator.iter_errors(changed)), field)
            for field in ['clauseId', 'hazardIds', 'basisLinkIds', 'dependencyFingerprint']:
                changed = copy.deepcopy(public)
                select(changed)[field] = 'UNAUTHORIZED'
                self.assertTrue(list(validator.iter_errors(changed)), field)
        for field, value in [('referenceOnly', False), ('currentDeterminationBasis', True),
                             ('reviewedCurrentClauseCount', 1), ('directHazardCount', 1),
                             ('standaloneDeterminationAllowed', True), ('allIndustryCoverage', True),
                             ('asOf', '2026-02-30'), ('asOf', '20261001'), ('firstLevelItemCount', -1),
                             ('sourceDocumentCount', True)]:
            changed = copy.deepcopy(public)
            changed[field] = value
            self.assertTrue(list(validator.iter_errors(changed)), field)
        for value in ['', False, '2026-02-30', '2026-1-1']:
            changed = copy.deepcopy(public)
            changed['readingGroups'][0]['documents'][1]['sourceIdentity']['effectiveDate'] = value
            self.assertTrue(list(validator.iter_errors(changed)))
        for value in ['https://evil.example/a', 'http://example.gov.cn/a', 'https://u:p@example.gov.cn/a',
                      'https://example.gov.cn:443/a', 'https://example.gov.cn/%0aa']:
            changed = copy.deepcopy(public)
            changed['readingGroups'][0]['publicationBasis']['legalSourceUrl'] = value
            self.assertTrue(list(validator.iter_errors(changed)), value)


class ReadingReleaseTests(unittest.TestCase):
    build = release_fixtures.FieldProfileReleaseTests.build
    read = release_fixtures.FieldProfileReleaseTests.read
    reseal = release_fixtures.FieldProfileReleaseTests.reseal
    verify = release_fixtures.FieldProfileReleaseTests.verify

    def setUp(self):
        self.r = ReadingTests()
        self.r.setUp()
        self.addCleanup(self.r.doCleanups)
        self.root, self.publication, self.fixture = self.r.root, self.r.pub, self.r.fixture
        self.fixture.hazard.update(note='', mode='direct', conditions='Synthetic exact source condition')
        self.fixture.entity('hazards', self.fixture.hazard)
        self.fixture.entity('links', self.fixture.link)
        self.fixture.approve_synthetic()
        self.fixture.put('manifest.json', {'synthetic': True})
        self.out, self.selection = self.root / 'source/releases/test', self.root / 'selection.json'
        directory_fixtures.DirectoryReleaseTests.add_required_library_entry(self)

    def test_release_registers_reading_and_keeps_original_current_projection_unchanged(self):
        self.build('2026-10-01')
        public = self.read(reading.READING_FILE)
        self.assertEqual((public['readingGroupCount'], public['sourceDocumentCount'], public['firstLevelItemCount']), (1, 2, 72))
        self.assertEqual(self.read('data/manifest.json')['files']['majorCriteriaReading'], reading.READING_FILE)
        counts = self.read('data/manifest.json')['counts']
        self.assertEqual((counts['majorCriteriaReadingGroups'], counts['majorCriteriaReadingDocuments'],
                          counts['majorCriteriaReadingFirstLevelItems']), (1, 2, 72))
        self.assertIn(reading.READING_FILE, self.read('site-manifest.json')['fileHashes'])
        self.assertIn(reading.NAMESPACE, release_snapshot.FORMAL_NAMESPACES)
        self.assertIn('check_major_criteria_reading', validate_all.BLOCKING)
        rc, report = self.verify()
        self.assertEqual(rc, 0, report)
        files = ['data/hazards/h0000.json', 'data/clauses/c0000.json', 'data/law-index.json', 'data/search-index.json']
        before = {rel: (self.out / rel).read_bytes() for rel in files}
        (self.root / reading.NAMESPACE / 'scope-reviews/READING_SYNTHETIC.json').unlink()
        self.build('2026-10-01')
        self.assertEqual(self.read(reading.READING_FILE)['readingGroups'], [])
        for rel in files:
            self.assertEqual((self.out / rel).read_bytes(), before[rel], rel)
        rc, report = self.verify()
        self.assertEqual(rc, 0, report)

    def test_resealed_public_mutations_and_count_mismatches_are_rejected(self):
        self.build('2026-10-01')
        original = self.read(reading.READING_FILE)
        mutations = [
            lambda p: p.update(currentDeterminationBasis=True),
            lambda p: p.update(reviewedCurrentClauseCount=72),
            lambda p: p.update(directHazardCount=1),
            lambda p: p.update(readingGroupCount=2),
            lambda p: p.update(sourceDocumentCount=1),
            lambda p: p.update(firstLevelItemCount=71),
            lambda p: p['readingGroups'][0]['documents'].pop(),
            lambda p: p['readingGroups'][0]['documents'][0].update(firstLevelItemCount=63),
            lambda p: p['readingGroups'][0]['documents'][0]['sections'][0]['items'][0].update(quote='Forged quotation'),
            lambda p: p['readingGroups'][0]['documents'][1]['sourceIdentity'].update(effectiveDate='2020-01-01'),
            lambda p: p['readingGroups'][0]['documents'][0]['officialClarifications'][0].update(text='Exception omitted'),
            lambda p: p['readingGroups'][0]['documents'][0]['officialClarifications'][0].update(isOfficialNormText=True),
            lambda p: p['readingGroups'][0].pop('publicationBasis'),
            lambda p: p['readingGroups'][0]['documents'][0].update(hazardIds=['H_FAKE']),
        ]
        for mutate in mutations:
            changed = copy.deepcopy(original)
            mutate(changed)
            (self.out / reading.READING_FILE).write_text(json.dumps(changed, ensure_ascii=False), encoding='utf-8')
            self.reseal()
            rc, report = self.verify()
            self.assertEqual(rc, 1, report)
            self.assertTrue(any('精确投影' in error or 'schema' in error.lower() for error in report['errors']), report)
            self.assertFalse(any('哈希' in error or 'Hash' in error for error in report['errors']), report)

    def test_consistently_resealed_manifest_counts_still_require_exact_reading_projection(self):
        self.build('2026-10-01')
        originals = {rel: self.read(rel) for rel in ['data/manifest.json', 'release.json', 'site-manifest.json']}
        for field, value in [('majorCriteriaReadingGroups', 2), ('majorCriteriaReadingDocuments', 1),
                             ('majorCriteriaReadingFirstLevelItems', 71)]:
            for rel, original in originals.items():
                changed = copy.deepcopy(original)
                if 'counts' in changed:
                    changed['counts'][field] = value
                (self.out / rel).write_text(json.dumps(changed, ensure_ascii=False), encoding='utf-8')
            self.reseal()
            rc, report = self.verify()
            self.assertEqual(rc, 1, report)
            self.assertTrue(any('重大判定计数不一致：' + field in error for error in report['errors']), report)
            self.assertFalse(any('哈希' in error or 'Hash' in error for error in report['errors']), report)


class ProductionReadingTests(unittest.TestCase):
    """Read-only regression against independently signed production sources."""
    @classmethod
    def setUpClass(cls):
        cls.knowledge, cls.publication = ROOT / 'knowledge', ROOT / 'source/publication'
        cls.before = reading.public_projection(cls.knowledge, cls.publication, as_of=date(2026, 9, 30))
        cls.after = reading.public_projection(cls.knowledge, cls.publication, as_of=AS_OF)

    def test_real_group_contains_64_plus_8_items_and_16_summaries_plus_pending_link(self):
        self.assertEqual(self.before['public']['readingGroupCount'], 0)
        public = self.after['public']
        original = [g for g in public['readingGroups'] if g['id'] not in {'READING_CIVIL_EXPLOSIVES_2024','READING_FIREWORKS_2017'}]
        self.assertEqual((len(original),sum(len(g['documents']) for g in original),sum(d['firstLevelItemCount'] for g in original for d in g['documents'])), (1,2,72), self.after['inventory'])
        documents = original[0]['documents']
        self.assertEqual([d['firstLevelItemCount'] for d in documents], [64, 8])
        notes = [n for d in documents for n in d['officialClarifications']]
        self.assertEqual(sum(n['textMode'] == 'reviewed_summary' for n in notes), 16)
        self.assertEqual(sum(n['textMode'] == 'official_link_pending' for n in notes), 1)
        supplement = next(d for d in documents if d['sourceIdentity']['directoryGroup']['role'] == 'supplement')
        self.assertIsNone(supplement['sourceIdentity']['effectiveDate'])
        self.assertEqual(supplement['sourceIdentity']['publicationDate'], '2024-04-23')
        self.assertFalse(public['currentDeterminationBasis'])
        self.assertEqual((public['reviewedCurrentClauseCount'], public['directHazardCount']), (0, 0))

    def test_real_current_criteria_remain_110_clauses_and_20_hazards(self):
        # This 2026-10-01 assertion belongs to its exact pre-complete source;
        # later evidence reviews must not be backdated into that historical view.
        from complete_remaining_cohort_fixture import pre_complete_repo_root
        historical_knowledge = pre_complete_repo_root(ROOT) / 'knowledge'
        projection = major.public_projection(historical_knowledge, as_of=AS_OF)
        clauses = {c['clauseId'] for s in projection['catalog']['standards'] for c in s['clauses']}
        self.assertEqual(len(clauses), 110)
        self.assertEqual(len(projection['topic']['hazardIds']), 20)
        reading_ids = {d['sourceIdentity']['lawVersionId'] for g in self.after['public']['readingGroups'] for d in g['documents']}
        self.assertTrue(reading_ids)
        self.assertFalse(reading_ids & {s['lawVersionId'] for s in projection['catalog']['standards']})


if __name__ == '__main__':
    unittest.main()
