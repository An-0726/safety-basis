"""Exact-source containment; history and source entities remain immutable.

Restoring rejected reviews below is an in-memory diagnostic only. It documents
the historical wrong admission and never creates a production approval.
"""
from commerce_cohort_fixture import pre_commerce_gate
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from field_profiles import ProfileContext, public_projection, review_bindings
import release_gate_core as gate

FIXTURE = json.loads((Path(__file__).parent / 'fixtures' /
                     'mem10_source_containment_20261001.json').read_text(encoding='utf-8'))
HIDS = {h for values in FIXTURE['clauseToHazards'].values() for h in values}
KIDS = {'K_XLSX_WEB_' + h for h in HIDS}


# This repair protects the original six; later independently reviewed profiles may be added.
ORIGINAL_PROFILE_IDS = {
    'FPR_EXTINGUISHER_ACCESS_BLOCKED',
    'FPR_EXTINGUISHER_BRACKET_OBSTRUCTION',
    'FPR_GAS_ALARM_FUNCTION_FAILURE',
    'FPR_ROUTING_JSXF_53_3',
    'FPR_ROUTING_JSXF_58_1',
    'FPR_ROUTING_JSXF_58_2',
}


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Mem10SourceContainmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        kinds = ('laws', 'law-versions', 'clauses', 'hazards', 'links')
        cls.current = {rel: gate.load_dir(KNOW, rel) for rel in kinds}
        cls.current.update({f'reviews/{rel}': gate.load_reviews(KNOW, f'reviews/{rel}')
                            for rel in kinds})

    def evaluate(self, state, day):
        def source(_root, rel):
            return copy.deepcopy(state[rel.replace('\\', '/')])
        with patch.object(gate, 'load_dir', source), patch.object(gate, 'load_reviews', source):
            return gate.evaluate_release_gate(KNOW, date.fromisoformat(day))

    def historical(self, kinds=('clauses', 'links')):
        state = copy.deepcopy(self.current)
        for row in FIXTURE['reviewChanges']:
            if row['entityType'] in kinds:
                state['reviews/' + row['entityType']][row['entityId']] = copy.deepcopy(row['oldReview'])
        return state

    def test_exact_six_rejections_preserve_full_prior_review_and_bindings(self):
        self.assertEqual(len(FIXTURE['reviewChanges']), 6)
        for row in FIXTURE['reviewChanges']:
            with self.subTest(path=row['path']):
                current = read(row['path'])
                self.assertEqual(current, row['newReview'])
                self.assertEqual(sha((ROOT / row['path']).read_bytes()), row['afterFileSha256'])
                self.assertEqual(current['decision'], 'rejected')
                self.assertEqual(current['previousReview'], row['oldReview'])
                self.assertEqual(current['previousReviewFileSha256'], row['beforeFileSha256'])
                self.assertEqual(current['reviewedContentHash'], row['oldReview']['reviewedContentHash'])
                self.assertEqual(current.get('contextHashes'), row['oldReview'].get('contextHashes'))
                self.assertEqual(current['evidenceRefs'], ['E_PDDB_L019'])
                self.assertEqual(current['reviewedContentHash'], content_hash(
                    read(row['path'].replace('/reviews', ''))))
                self.assertIn('重新', current['reason'])

    def test_entities_ids_lifecycle_and_hazard_definition_reviews_unchanged(self):
        for path, expected in FIXTURE['preservedFileSha256'].items():
            with self.subTest(path=path):
                self.assertEqual(sha((ROOT / path).read_bytes()), expected)
        for hid in HIDS:
            self.assertEqual(self.current['hazards'][hid]['lifecycle'], 'active')
            self.assertEqual(self.current['reviews/hazards'][hid]['decision'], 'verified')

    def test_exact_inbound_links_no_invented_alternative_basis(self):
        for cid, ids in FIXTURE['clauseToHazards'].items():
            actual = {link['hazardId'] for link in self.current['links'].values()
                      if link['clauseId'] == cid}
            self.assertEqual(actual, set(ids))
        for hid in HIDS:
            self.assertEqual({link['id'] for link in self.current['links'].values()
                              if link['hazardId'] == hid}, {'K_XLSX_WEB_' + hid})

    def test_current_and_historical_date_gates_exclude_exact_four_chains(self):
        for expected in FIXTURE['prediction']:
            with self.subTest(day=expected['asOf']):
                current = self.evaluate(self.current, expected['asOf'])
                historical = self.evaluate(self.historical(), expected['asOf'])
                self.assertEqual(set(historical.eligible_hazards) - set(current.eligible_hazards), HIDS)
                self.assertEqual(set(historical.eligible_links) - set(current.eligible_links), KIDS)
                self.assertFalse(set(current.eligible_hazards) - set(historical.eligible_hazards))
                self.assertFalse(set(current.eligible_links) - set(historical.eligible_links))
                self.assertEqual(len(pre_commerce_gate(current).eligible_hazards), 1653)
                self.assertEqual(len(pre_commerce_gate(current).eligible_links), 1787)
                self.assertEqual(len({current.links[k]['clauseId'] for k in pre_commerce_gate(current).eligible_links}), 1338)
                self.assertEqual(len(pre_commerce_gate(historical).eligible_hazards), 1657)
                self.assertEqual(len(pre_commerce_gate(historical).eligible_links), 1791)
                self.assertEqual(len({historical.links[k]['clauseId'] for k in pre_commerce_gate(historical).eligible_links}), 1340)
                for cid in FIXTURE['clauseToHazards']:
                    self.assertFalse(current.clauses[cid]['ok'])

    def test_restoring_only_clause_or_only_link_cannot_bypass_other_rejection(self):
        for kinds in [('clauses',), ('links',)]:
            with self.subTest(restored=kinds):
                result = self.evaluate(self.historical(kinds), '2026-10-01')
                self.assertFalse(HIDS & set(result.eligible_hazards))
                self.assertFalse(KIDS & set(result.eligible_links))

    def test_all_six_governed_profiles_and_dependencies_are_unchanged(self):
        current = ProfileContext(KNOW)
        before = copy.deepcopy(current)
        for row in FIXTURE['reviewChanges']:
            before.reviews[row['entityType']][row['entityId']] = row['oldReview']
        records = [json.loads(p.read_text(encoding='utf-8'))
                   for p in (KNOW / 'field-profiles/v1/records').glob('*.json')]
        self.assertTrue(ORIGINAL_PROFILE_IDS <= {profile['id'] for profile in records})
        for profile in records:
            self.assertEqual(review_bindings(profile, current), review_bindings(profile, before))
        published_ids = {profile['id'] for profile in
                         public_projection(KNOW, as_of=date(2026, 10, 1))['public']['records']}
        self.assertTrue(ORIGINAL_PROFILE_IDS <= published_ids)

    def test_paraphrase_issue_and_existing_correct_full_article_not_silently_repaired(self):
        clause = read('knowledge/clauses/C_MEM10_8_7.json')
        full = read('knowledge/clauses/C_PDDB_8.json')
        self.assertTrue(clause['quote'].startswith('轻工行业企业'))
        self.assertTrue(full['quote'].startswith('第八条轻工企业'))
        self.assertEqual(clause['articlePath'], '第八条第（七）项')
        self.assertNotIn('C_MEM10_8_7', FIXTURE['clauseToHazards'])
        # A separately reviewed follow-up relocates its link, tested by
        # test_mem10_paraphrase_repair. The source fragment stays unchanged.


if __name__ == '__main__':
    unittest.main()
