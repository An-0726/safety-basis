"""Synthetic reviews only: complete official document text needs a separate review."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v4'))
import major_criteria as major
from canonical import content_hash
from field_profiles import ProfileContext
import test_field_profiles as fixtures
from test_major_criteria import synthetic_config


class FullDocumentTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.FieldProfileTests(); self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.config = synthetic_config(self.f); self.s = self.config['standards'][0]
        self.s['topicLinks'] = []
        self.s['officialScope']['wholeStandardComplete'] = True
        self.s['publication'] = {'basis': major.PUBLICATION_BASIS,
            'legalSourceUrl': 'https://example.gov.cn/copyright', 'evidenceIds': ['E_RIGHTS']}
        self.f.put('evidence/E_RIGHTS.json', {'id': 'E_RIGHTS', 'url': 'https://example.gov.cn/copyright',
            'tier': 'authoritative-public', 'snapshotSha256': 'a' * 64, 'locator': 'Article 5'})
        p = self.f.root / 'reviews/law-versions/LV_TEST.json'
        r = json.loads(p.read_text()); r['fullQuotePublicationReady'] = False
        self.f.put('reviews/law-versions/LV_TEST.json', r)
        self.save()

    def save(self): self.f.put(major.CONFIG_PATH, self.config)
    def project(self): return major.public_projection(self.f.root, as_of=date(2026, 9, 30))
    def approve(self):
        binding, _ = major.scope_review_bindings(self.s, self.f.root)
        self.review = {'schemaVersion': 1, 'lawVersionId': 'LV_TEST', 'decision': 'verified',
            **binding, 'checkedAt': '2026-09-30T08:00:00+00:00', 'reviewScope': major.SCOPE_REVIEW,
            'fullQuotePublicationReady': True, 'reviewer': 'Synthetic reviewer', 'reason': 'Synthetic test only'}
        self.write_review()
    def write_review(self): self.f.put('major-criteria/v1/reviews/LV_TEST.json', self.review)

    def test_new_complete_claim_and_metadata_only_review_cannot_self_approve(self):
        self.assertEqual(self.project()['catalog']['standards'], [])
        self.s['officialScope']['wholeStandardComplete'] = False
        del self.s['publication']; self.save()
        self.assertEqual(self.project()['catalog']['standards'], [])

    def test_independent_binding_publishes_complete_body_without_hazards(self):
        self.approve(); result = self.project(); row = result['catalog']['standards'][0]
        self.assertTrue(row['coverage']['wholeStandardComplete'])
        self.assertEqual(row['directHazardCount'], 0)
        self.assertEqual(result['topic']['hazardIds'], [])
        self.assertEqual(row['publicationBasis']['legalSourceUrl'], self.s['publication']['legalSourceUrl'])
        self.assertNotIn('reviewer', json.dumps(result['catalog']))

    def test_complete_selected_body_can_explicitly_exclude_an_official_appendix(self):
        self.s['officialScope']['wholeStandardComplete'] = False
        self.s['officialScope']['label'] = 'All selected articles; official report-form appendix is linked, not reproduced'
        self.save(); self.approve()
        row = self.project()['catalog']['standards'][0]
        self.assertEqual(row['coverage']['status'], 'reviewed_scope_complete')
        self.assertFalse(row['coverage']['wholeStandardComplete'])
        self.assertFalse(row['officialScope']['wholeStandardComplete'])

    def test_selected_body_is_atomic_even_without_whole_document_claim(self):
        self.s['officialScope']['wholeStandardComplete'] = False
        second = {**self.f.clause, 'id': 'C_SECOND', 'quote': '2 Synthetic scope definition'}
        self.f.entity('clauses', second)
        self.s['clauses'].append({'clauseId': second['id'], 'contentHash': content_hash(second),
            'granularity': 'whole_clause', 'judgmentItemCount': 0})
        path = 'reviews/clauses/C_SECOND.json'
        review = json.loads((self.f.root / path).read_text())
        review['decision'] = 'rejected'; self.f.put(path, review)
        self.save(); self.approve()
        result = self.project()
        self.assertEqual(result['catalog']['standards'], [])
        self.assertIn('COMPLETE_BODY_INCOMPLETE', [row['reason'] for row in result['inventory']['excluded']])

    def test_missing_future_invalid_rejected_and_wrong_scope_reviews_fail_closed(self):
        self.approve(); original = copy.deepcopy(self.review)
        for change in ({'decision': 'proposed'}, {'checkedAt': '2026-10-01'}, {'checkedAt': '2026-02-30'},
                       {'checkedAt': '2026-09-30T08:00:00'}, {'reviewScope': 'metadata_only'},
                       {'fullQuotePublicationReady': False}, {'schemaVersion': True},
                       {'lawVersionId': 'LV_OTHER'}, {'reviewedContentHash': '0' * 64},
                       {'dependencyFingerprint': '0' * 64}):
            with self.subTest(change=change):
                self.review = {**original, **change}; self.write_review()
                self.assertEqual(self.project()['catalog']['standards'], [])

    def test_selection_scope_and_upstream_review_changes_invalidate_review(self):
        self.approve(); self.s['officialScope']['label'] = 'Different asserted scope'; self.save()
        self.assertEqual(self.project()['catalog']['standards'], [])
        self.approve()
        p = self.f.root / 'reviews/clauses/C_TEST.json'; r = json.loads(p.read_text())
        r['reason'] = 'A newly reviewed dependency'; self.f.put('reviews/clauses/C_TEST.json', r)
        self.assertEqual(self.project()['catalog']['standards'], [])

    def test_missing_or_mismatched_rights_evidence_is_not_permission(self):
        self.approve(); p = self.f.root / 'evidence/E_RIGHTS.json'
        original = json.loads(p.read_text())
        for change in ({'url': 'https://example.gov.cn/unrelated'}, {'tier': 'third-party'},
                       {'snapshotSha256': ''}, {'locator': ''}):
            self.f.put('evidence/E_RIGHTS.json', {**original, **change}); self.approve()
            self.assertEqual(self.project()['catalog']['standards'], [])
        p.unlink(); self.approve()
        self.assertEqual(self.project()['catalog']['standards'], [])

    def test_complete_body_never_survives_a_clause_gate_failure(self):
        p = self.f.root / 'reviews/clauses/C_TEST.json'; r = json.loads(p.read_text())
        r['decision'] = 'rejected'; self.f.put('reviews/clauses/C_TEST.json', r)
        self.approve()
        self.assertEqual(self.project()['catalog']['standards'], [])

    def test_whole_claim_without_explicit_publication_fields_is_invalid(self):
        del self.s['publication']; self.save()
        with self.assertRaisesRegex(ValueError, 'WHOLE_SCOPE_REVIEW_REQUIRED'): self.project()

    def test_bindings_are_read_only_and_include_exact_source_chain(self):
        before = sorted(str(p.relative_to(self.f.root)) for p in self.f.root.rglob('*.json'))
        hashes, deps = major.scope_review_bindings(self.s, self.f.root)
        self.assertEqual(hashes['reviewedContentHash'], content_hash(self.s))
        self.assertIn('reviews/clauses/C_TEST', deps); self.assertIn('evidence/E_RIGHTS', deps)
        self.assertEqual(before, sorted(str(p.relative_to(self.f.root)) for p in self.f.root.rglob('*.json')))


if __name__ == '__main__': unittest.main()
