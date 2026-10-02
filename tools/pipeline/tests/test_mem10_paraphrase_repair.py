"""A separately reviewed exact-source relocation, not a new major finding."""
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
                     'mem10_paraphrase_repair_20261001.json').read_text(encoding='utf-8'))
HID, KID, OLD_C, NEW_C = (FIXTURE[k] for k in
                         ('hazardId', 'linkId', 'oldClauseId', 'targetClauseId'))


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


class Mem10ParaphraseRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        groups = ('laws', 'law-versions', 'clauses', 'hazards', 'links')
        cls.current = {rel: gate.load_dir(KNOW, rel) for rel in groups}
        cls.current.update({f'reviews/{rel}': gate.load_reviews(KNOW, f'reviews/{rel}')
                            for rel in groups})

    def evaluate(self, state, day='2026-10-01'):
        def source(_root, rel):
            return copy.deepcopy(state[rel.replace('\\', '/')])
        with patch.object(gate, 'load_dir', source), patch.object(gate, 'load_reviews', source):
            return gate.evaluate_release_gate(KNOW, date.fromisoformat(day))

    def historical(self):
        state = copy.deepcopy(self.current)
        for row in FIXTURE['changes']:
            parts = row['path'].split('/')
            namespace = '/'.join(parts[1:-1])
            obj = row['oldRecord']
            state[namespace][obj.get('entityId', obj.get('id'))] = copy.deepcopy(obj)
        return state

    def test_exact_three_records_and_only_two_link_fields_change(self):
        self.assertEqual(len(FIXTURE['changes']), 3)
        for row in FIXTURE['changes']:
            with self.subTest(path=row['path']):
                self.assertEqual(read(row['path']), row['newRecord'])
                self.assertEqual(sha((ROOT / row['path']).read_bytes()), row['afterFileSha256'])
        link_change = next(x for x in FIXTURE['changes'] if x['path'].startswith('knowledge/links/'))
        self.assertEqual(set(link_change['changedFields']), {'clauseId', 'applicability'})
        self.assertEqual(link_change['oldRecord']['id'], link_change['newRecord']['id'])
        self.assertEqual(link_change['oldRecord']['lifecycle'], link_change['newRecord']['lifecycle'])

    def test_hazard_full_article_fragment_and_prior_fixture_bytes_unchanged(self):
        for path, expected in FIXTURE['preservedFileSha256'].items():
            with self.subTest(path=path):
                self.assertEqual(sha((ROOT / path).read_bytes()), expected)
        self.assertEqual(sha((Path(__file__).parent / 'fixtures' /
                              'mem10_source_containment_20261001.json').read_bytes()),
                         FIXTURE['stage1FixtureSha256'])

    def test_explicit_review_scope_and_both_previous_reviews_preserved(self):
        link = self.current['links'][KID]
        current = self.current['reviews/links'][KID]
        original = self.historical()['reviews/links'][KID]
        self.assertEqual(current['decision'], 'verified')
        self.assertEqual(current['reviewedContentHash'], content_hash(link))
        self.assertEqual(current['contextHashes'], {
            'hazard': content_hash(self.current['hazards'][HID]),
            'clause': content_hash(self.current['clauses'][NEW_C]),
        })
        self.assertEqual(current['previousReview'], original)
        rejected = self.current['reviews/clauses'][OLD_C]
        self.assertEqual(rejected['decision'], 'rejected')
        self.assertEqual(rejected['previousReview'], self.historical()['reviews/clauses'][OLD_C])
        self.assertEqual(rejected['reviewedContentHash'], content_hash(self.current['clauses'][OLD_C]))
        for row in FIXTURE['changes']:
            if '/reviews/' in row['path']:
                self.assertEqual(row['newRecord']['previousReviewFileSha256'], row['beforeFileSha256'])

    def test_full_article_is_selected_only_for_light_industry_paragraph_seven(self):
        link = self.current['links'][KID]
        self.assertEqual(link['clauseId'], NEW_C)
        self.assertIn('轻工企业', link['applicability'])
        self.assertIn('第八条第（七）项', link['applicability'])
        self.assertIn('故障电池', link['applicability'])
        self.assertIn('不将其他分项自动套用', link['applicability'])
        self.assertEqual(self.current['clauses'][NEW_C]['articlePath'], '第8条')
        self.assertTrue(self.current['clauses'][NEW_C]['quote'].startswith('第八条轻工企业'))
        # This source contract must be honored by downstream topic/detail UI;
        # it does not claim that the old generic detail UI already renders it.

    def test_two_date_gate_swaps_exact_clause_without_losing_or_adding_hazards(self):
        for day in ('2026-09-30', '2026-10-01'):
            with self.subTest(day=day):
                current = self.evaluate(self.current, day)
                before = self.evaluate(self.historical(), day)
                self.assertEqual(current.eligible_hazards, before.eligible_hazards)
                self.assertEqual(current.eligible_links, before.eligible_links)
                self.assertIn(HID, current.eligible_hazards)
                self.assertIn(KID, current.eligible_links)
                self.assertFalse(current.clauses[OLD_C]['ok'])
                self.assertTrue(current.clauses[NEW_C]['ok'])
                now_clauses = {current.links[k]['clauseId'] for k in current.eligible_links}
                old_clauses = {before.links[k]['clauseId'] for k in before.eligible_links}
                self.assertEqual(old_clauses - now_clauses, {OLD_C})
                self.assertEqual(now_clauses - old_clauses, {NEW_C})
                cohort = pre_commerce_gate(current)
                cohort_clauses = {current.links[k]['clauseId'] for k in cohort.eligible_links}
                self.assertEqual((len(cohort.eligible_hazards), len(cohort.eligible_links), len(cohort_clauses)),
                                 (1653, 1787, 1338))

    def test_stale_review_or_scope_edits_do_not_gain_automatic_admission(self):
        state = copy.deepcopy(self.current)
        state['reviews/links'][KID] = self.historical()['reviews/links'][KID]
        self.assertNotIn(HID, self.evaluate(state).eligible_hazards)
        state = copy.deepcopy(self.current)
        state['reviews/links'][KID]['contextHashes']['clause'] = content_hash(self.current['clauses'][OLD_C])
        self.assertNotIn(KID, self.evaluate(state).eligible_links)
        state = copy.deepcopy(self.current)
        state['links'][KID]['applicability'] = '所有仓库'
        self.assertNotIn(KID, self.evaluate(state).eligible_links)

    def test_six_governed_profiles_have_no_dependency_drift(self):
        ctx = ProfileContext(KNOW)
        before = copy.deepcopy(ctx)
        for row in FIXTURE['changes']:
            parts = row['path'].split('/')
            obj = row['oldRecord']
            if parts[1] == 'reviews':
                before.reviews[parts[2]][obj['entityId']] = obj
            else:
                before.entities[parts[1]][obj['id']] = obj
        for path in (KNOW / 'field-profiles/v1/records').glob('*.json'):
            profile = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(review_bindings(profile, ctx), review_bindings(profile, before))
        published_ids = {profile['id'] for profile in
                         public_projection(KNOW, as_of=date(2026, 10, 1))['public']['records']}
        self.assertTrue(ORIGINAL_PROFILE_IDS <= published_ids)


if __name__ == '__main__':
    unittest.main()
