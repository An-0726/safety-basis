import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
from recovery_cohort_fixture import pre_recovery_repo_root, evaluate_historical_snapshot
# This dated cohort is tested against its SHA-guarded predecessor, not new admissions.
ROOT = pre_recovery_repo_root(ROOT)
sys.path.insert(0, str(ROOT/'tools/v4'))
from check_commerce_candidate_dispositions import LEDGER, INDEPENDENT_REVIEW, validate_rows, validate_independent_review, CONTINUATION_REVIEW, ATOMIC_SPLITS, validate_atomic_splits


class CommerceDispositionTests(unittest.TestCase):
    def setUp(self):
        self.rows = [json.loads(x) for x in (ROOT/LEDGER).read_text(encoding='utf-8').splitlines()]
        self.hazards = {x['id']: x for p in (ROOT/'knowledge/hazards').glob('*.json') for x in [json.loads(p.read_text(encoding='utf-8'))]}
        self.reviews = {x['entityId']: x for p in (ROOT/'knowledge/reviews/hazards').glob('*.json') for x in [json.loads(p.read_text(encoding='utf-8'))]}
        self.sources = [json.loads(x) for x in (ROOT/'docs/commerce-ingest-map-20260921.jsonl').read_text(encoding='utf-8').splitlines()]

    def check(self):
        return validate_rows(self.rows, self.hazards, self.reviews, self.sources)

    def test_all_44_applied_records_reconcile(self):
        self.assertEqual(self.check(), [])

    def test_duplicate_or_missing_candidate_fails(self):
        self.rows[-1] = copy.deepcopy(self.rows[0])
        self.assertTrue(any('44 unique' in x for x in self.check()))

    def test_unrecorded_entity_change_fails(self):
        self.hazards[self.rows[0]['hazardId']]['conditions'] += ' unexpected scope'
        self.assertTrue(any('stale' in x for x in self.check()))

    def test_original_row_lineage_cannot_be_dropped(self):
        self.rows[0]['sourceCandidateIds'] = []
        self.assertTrue(any('source row lineage' in x for x in self.check()))

    def test_site_finding_and_completion_cannot_be_inferred(self):
        self.rows[0]['fieldViolationEstablished'] = True
        self.rows[1]['remediationEstablished'] = True
        self.assertEqual(sum('must not establish' in x for x in self.check()), 2)

    def test_merge_must_be_applied_to_valid_target(self):
        row = next(x for x in self.rows if x['action'] == 'merged_conditionally')
        self.hazards[row['hazardId']]['mergedInto'] = None
        self.assertTrue(any('merge not applied' in x for x in self.check()))

    def test_target_change_requires_new_scope_review(self):
        row = next(x for x in self.rows if x['action'] == 'merged_conditionally')
        self.hazards[row['canonicalHazardId']]['conditions'] += ' changed'
        self.assertTrue(any('target changed' in x for x in self.check()))

    def test_out_of_scope_is_rejected_and_not_active(self):
        row = next(x for x in self.rows if x['action'] == 'out_of_scope')
        self.reviews[row['hazardId']]['decision'] = 'verified'
        self.assertTrue(any('incorrect review decision' in x for x in self.check()))

    def test_unresolved_record_cannot_gain_public_eligibility(self):
        row = next(x for x in self.rows if x['action'] == 'verification_protocol_complete')
        row['releaseEligibleByThisDisposition'] = True
        self.assertTrue(any('must not grant' in x for x in self.check()))

    def test_every_record_has_retraced_original_statement(self):
        self.assertTrue(all(r['sourceRead']['originalStatementMatched'] for r in self.rows))
        self.assertTrue(all(not r['sourceRead']['photosOrFunctionalTestsVerified'] for r in self.rows))

    def independent_input(self):
        independent = json.loads((ROOT/INDEPENDENT_REVIEW).read_text(encoding='utf-8'))
        continuation = json.loads((ROOT/CONTINUATION_REVIEW).read_text(encoding='utf-8'))
        independent['items'] += continuation['items']
        self.atomic_rows = json.loads((ROOT/ATOMIC_SPLITS).read_text(encoding='utf-8'))['items']
        entities = {'hazards': self.hazards}
        for folder in ['links', 'clauses', 'law-versions']:
            entities[folder] = {x['id']: x for p in (ROOT/'knowledge'/folder).glob('*.json')
                               for x in [json.loads(p.read_text(encoding='utf-8'))]}
        return independent, entities

    def test_two_independent_rounds_match_exact_current_entities(self):
        independent, entities = self.independent_input()
        self.assertEqual(validate_independent_review(self.rows, independent, entities, self.atomic_rows), [])

    def test_independent_review_cannot_hide_a_later_version_source_change(self):
        independent, entities = self.independent_input()
        entities['law-versions']['LV_STD_GB50303_2015']['sourceUrl'] = 'https://example.invalid/wrong'
        self.assertTrue(any('independent review stale' in x for x in
                            validate_independent_review(self.rows, independent, entities, self.atomic_rows)))

    def test_independent_review_cannot_silently_drop_or_add_an_admission(self):
        independent, entities = self.independent_input()
        independent['items'].pop()
        self.assertTrue(any('exact applied' in x for x in
                            validate_independent_review(self.rows, independent, entities, self.atomic_rows)))

    def test_independent_review_cannot_assert_unseen_site_facts(self):
        independent, entities = self.independent_input()
        independent['items'][0]['siteFactEstablished'] = True
        self.assertTrue(any('scope/currency decision differs' in x for x in
                            validate_independent_review(self.rows, independent, entities, self.atomic_rows)))

    def test_atomic_split_exact_lineage_and_original_predicate_are_preserved(self):
        _, entities = self.independent_input()
        self.assertEqual(validate_atomic_splits(self.atomic_rows, self.rows, self.sources, entities), [])

    def test_atomic_split_cannot_fake_a_fresh_original_read(self):
        _, entities = self.independent_input()
        self.atomic_rows[0]['sourceRead']['originalStatementMatched'] = True
        self.assertTrue(any('original-file' in e for e in validate_atomic_splits(self.atomic_rows, self.rows, self.sources, entities)))

    def test_excluded_unsupported_claim_cannot_become_verified(self):
        row = next(x for x in self.rows if x['action'] == 'excluded_unsupported_claim')
        self.reviews[row['hazardId']]['decision'] = 'verified'
        self.assertTrue(any('incorrect review decision' in e for e in self.check()))

    def test_atomic_source_mapping_cannot_fake_an_observed_finding(self):
        _, entities = self.independent_input()
        source = next(s for s in self.sources if s['candidateId'] == 'SC118')
        mapping = next(m for m in source['mappedHazards'] if m.get('hazardId') == 'H_COM_MOBILE_ELECTRIC_CORD_SELECTION')
        mapping['fieldViolationEstablished'] = True
        self.assertTrue(any('field finding' in e for e in validate_atomic_splits(self.atomic_rows, self.rows, self.sources, entities)))

    def test_atomic_source_mapping_cannot_switch_to_a_different_record(self):
        _, entities = self.independent_input()
        source = next(s for s in self.sources if s['candidateId'] == 'SC118')
        source['sources'] = ['D01']
        self.assertTrue(any('SC118/D15' in e for e in validate_atomic_splits(self.atomic_rows, self.rows, self.sources, entities)))


if __name__ == '__main__':
    unittest.main()
