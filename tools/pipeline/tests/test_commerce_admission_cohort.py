"""Independently pin the commerce admission delta and pre-existing release set.

The fixture is an explicit, reviewed commit/ID/source receipt. Tests do not
approve arbitrary future additions discovered from the working tree, change
Gate policy, or equate a published generic definition with a site finding.
"""
from collections import Counter
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

from citation_cohort_fixture import (pre_citation_gate, pre_citation_ids,
                                    ADDED_IDS as CITATION_ADDED_IDS)
from common_hazards_fixture import (pre_common_ids, pre_common_gate,
                                    ADDED_IDS as COMMON_ADDED_IDS)
from commerce_cohort_fixture import (
    ADDED_IDS, ADMITTED_IDS, CANDIDATE_IDS, FIXTURE, FOLDERS,
    pre_commerce_gate, pre_commerce_ids, pre_commerce_inventory,
    pre_commerce_manifest,
)

ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def ids_sha256(ids):
    return hashlib.sha256(json.dumps(sorted(ids), ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


class CommerceAdmissionCohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = read(KNOW / 'manifest.json')
        cls.ledger = [json.loads(line) for line in
                      (ROOT / 'docs/commerce-candidate-dispositions-20261002.jsonl')
                      .read_text(encoding='utf-8').splitlines()]
        cls.by_hazard = {row['hazardId']: row for row in cls.ledger}
        cls.atomic = read(ROOT / 'docs/commerce-remaining-gap-atomic-splits-20261002.json')['items']
        cls.all_admitted_rows = dict(cls.by_hazard, **{r['hazardId']:r for r in cls.atomic})
        cls.entities = {kind: {row['id']: row for p in (KNOW / kind).glob('*.json')
                              for row in [read(p)]}
                        for kind in FOLDERS.values()}

    def test_manifest_records_the_exact_reviewed_commit_and_entity_delta(self):
        batches = [b for b in self.manifest['batches'] if b['id'] == FIXTURE['batchId']]
        self.assertEqual(len(batches), 1)
        batch = batches[0]
        self.assertEqual(batch['baselineCommit'], FIXTURE['baselineCommit'])
        self.assertEqual(batch, FIXTURE['originalBatchReceipt'])
        continuation = [b for b in self.manifest['batches'] if b['id'] == FIXTURE['continuationBatchReceipt']['id']]
        self.assertEqual(len(continuation), 1)
        # Review metadata is bound by the disposition checker, not this inventory receipt.
        actual = dict(continuation[0]); expected = dict(FIXTURE['continuationBatchReceipt'])
        for key in ['independentLegalReview', 'independentReviewRef', 'independentReviewSha256']:
            actual.pop(key, None); expected.pop(key, None)
        self.assertEqual(actual, expected)
        self.assertEqual(actual['hazardsAdmitted'], 9)
        self.assertEqual(actual['existingCandidatesAdmitted'], 8)
        self.assertEqual(actual['newAtomicHazardsAdmitted'], 1)
        union = {k: sorted(set(batch['addedEntityIds'][k] + actual['addedEntityIds'][k])) for k in FIXTURE['addedEntityIds']}
        self.assertEqual(union, FIXTURE['addedEntityIds'])

    def test_exact_inventory_delta_preserves_every_original_canonical_id(self):
        for key, kind in FOLDERS.items():
            with self.subTest(kind=kind):
                current = set(self.entities[kind])
                added = ADDED_IDS[kind]
                self.assertTrue(added <= current)
                historical = pre_common_ids(kind, pre_citation_ids(kind, current)) - added
                expected = FIXTURE['baselineInventory'][key]
                self.assertEqual(len(historical), expected['count'])
                self.assertEqual(ids_sha256(historical), expected['idsSha256'])
                self.assertEqual(self.manifest['counts'][key], len(current))
        self.assertEqual(ADDED_IDS['hazards'], frozenset(FIXTURE['newAtomicHazardIds']))
        self.assertEqual(ADDED_IDS['successions'], frozenset())

    def test_all_44_exact_original_source_mappings_and_prior_hashes_are_retained(self):
        self.assertEqual(len(self.ledger), 44)
        self.assertEqual(set(self.by_hazard), CANDIDATE_IDS)
        ingest = [json.loads(line) for line in
                  (ROOT / 'docs/commerce-ingest-map-20260921.jsonl')
                  .read_text(encoding='utf-8').splitlines()]
        for hid, expected in FIXTURE['candidateSources'].items():
            with self.subTest(hazard=hid):
                row = self.by_hazard[hid]
                self.assertEqual({key: row[key] for key in expected}, expected)
                disposition = FIXTURE['candidateDispositions'][hid]
                self.assertEqual({key: row[key] for key in disposition}, disposition)
                original_rows = [source for source in ingest
                                 if hid in {h['hazardId'] for h in source['mappedHazards']}]
                self.assertEqual(sorted(source['candidateId'] for source in original_rows),
                                 expected['sourceCandidateIds'])
                self.assertEqual(sorted({code for source in original_rows
                                         for code in source['sources']}),
                                 expected['sourceDocumentCodes'])
                self.assertEqual(row['appliedContentHash'], content_hash(self.entities['hazards'][hid]))
                self.assertEqual(row['appliedLifecycle'], self.entities['hazards'][hid]['lifecycle'])
                self.assertIs(row['fieldViolationEstablished'], False)
                self.assertIs(row['remediationEstablished'], False)

    def test_exact_two_round_dispositions_and_atomic_split_are_explicit(self):
        active = {hid for hid in CANDIDATE_IDS if self.entities['hazards'][hid]['lifecycle'] == 'active'}
        merged = {hid for hid in CANDIDATE_IDS if self.entities['hazards'][hid]['lifecycle'] == 'superseded'}
        excluded = {hid for hid, row in self.by_hazard.items() if row['action'] == 'out_of_scope'}
        self.assertEqual(active, ADMITTED_IDS - set(FIXTURE['newAtomicHazardIds']))
        self.assertEqual(merged, set(FIXTURE['mergedHazardIds']))
        self.assertEqual(excluded, set(FIXTURE['outOfScopeHazardIds']))
        self.assertEqual((len(active), len(merged), len(excluded)), (26, 7, 1))
        unsupported = set(FIXTURE['unsupportedClaimHazardIds'])
        pending = CANDIDATE_IDS - active - merged - excluded - unsupported
        self.assertEqual(unsupported, {hid for hid, row in self.by_hazard.items() if row['action'] == 'excluded_unsupported_claim'})
        self.assertEqual(len(unsupported), 9)
        self.assertEqual(pending, set(FIXTURE['verificationProtocolIds']))
        for hid in pending | excluded | unsupported:
            self.assertEqual(self.entities['hazards'][hid]['lifecycle'], 'proposed')
        self.assertIn('H_COM_BREAKER_LABEL_OBSCURED', active)
        self.assertIn('H_COM_PLUGSTRIP_COMBUSTIBLE', unsupported)
        self.assertEqual(self.manifest['lifecycle'],
                         Counter(h['lifecycle'] for h in self.entities['hazards'].values()))

    def test_every_new_link_is_an_exact_admitted_source_chain(self):
        ledger_links = {kid for hid in ADMITTED_IDS
                        for kid in self.all_admitted_rows[hid]['appliedLinkIds']}
        self.assertEqual(ledger_links, ADDED_IDS['links'])
        actual_incoming = {kid for kid, link in self.entities['links'].items()
                           if link['hazardId'] in ADMITTED_IDS}
        self.assertEqual(actual_incoming, ADDED_IDS['links'])
        for kid in ADDED_IDS['links']:
            with self.subTest(link=kid):
                link = self.entities['links'][kid]
                clause = self.entities['clauses'][link['clauseId']]
                self.assertIn(link['hazardId'], ADMITTED_IDS)
                version = self.entities['law-versions'][clause['lawVersionId']]
                self.assertIn(version['lawId'], self.entities['laws'])
                review = read(KNOW / 'reviews/links' / f'{kid}.json')
                self.assertEqual(review['decision'], 'verified')
                self.assertEqual(review['reviewedContentHash'], content_hash(link))
                self.assertEqual(review['contextHashes']['hazard'],
                                 content_hash(self.entities['hazards'][link['hazardId']]))
                self.assertEqual(review['contextHashes']['clause'], content_hash(clause))
                self.assertTrue(review['evidenceRefs'])
                self.assertTrue(set(review['evidenceRefs']) <= set(self.entities['evidence']))

    def assert_exact_release_cohort(self, gate):
        """One exact-set contract shared by the real Gate and negative mutations."""
        self.assertEqual(set(gate.eligible_hazards) & (CANDIDATE_IDS | set(FIXTURE['newAtomicHazardIds'])), ADMITTED_IDS)
        self.assertTrue(ADDED_IDS['links'] <= set(gate.eligible_links))
        historical = pre_commerce_gate(gate)
        for key, ids in [('eligibleHazards', historical.eligible_hazards),
                         ('eligibleLinks', historical.eligible_links)]:
            expected = FIXTURE['baselineGate'][key]
            self.assertEqual(len(ids), expected['count'], key)
            self.assertEqual(ids_sha256(ids), expected['idsSha256'], key)
        self.assertEqual(len(pre_common_gate(pre_citation_gate(gate)).eligible_hazards), 1653 + len(ADMITTED_IDS))
        self.assertEqual(len(pre_common_gate(pre_citation_gate(gate)).eligible_links), 1787 + len(ADDED_IDS['links']))
        self.assertFalse((CANDIDATE_IDS - ADMITTED_IDS) & set(gate.eligible_hazards))


    def test_real_gate_adds_only_exact_reviewed_two_round_hazards_and_keeps_old_set(self):
        self.assert_exact_release_cohort(evaluate_release_gate(KNOW, date(2026, 10, 2)))

    def test_exact_release_contract_rejects_an_unadmitted_candidate(self):
        gate = copy.deepcopy(evaluate_release_gate(KNOW, date(2026, 10, 2)))
        hid = 'H_COM_FORKLIFT_INFO_VERIFY'
        self.assertNotIn(hid, gate.eligible_hazards)
        gate.eligible_hazards.add(hid)
        with self.assertRaises(AssertionError):
            self.assert_exact_release_cohort(gate)

    def test_exact_release_contract_rejects_loss_of_a_pre_existing_hazard(self):
        gate = copy.deepcopy(evaluate_release_gate(KNOW, date(2026, 10, 2)))
        self.assertIn('H001', gate.eligible_hazards)
        self.assertNotIn('H001', CANDIDATE_IDS)
        gate.eligible_hazards.remove('H001')
        with self.assertRaises(AssertionError):
            self.assert_exact_release_cohort(gate)

    def test_exact_release_contract_rejects_restoring_an_old_rejected_hazard(self):
        gate = copy.deepcopy(evaluate_release_gate(KNOW, date(2026, 10, 2)))
        hid = 'H_12158_10_1_2'
        self.assertNotIn(hid, gate.eligible_hazards)
        self.assertIn('BLOCK_REVIEW_NOT_VERIFIED:rejected', gate.hazards[hid]['reasons'])
        gate.eligible_hazards.add(hid)
        with self.assertRaises(AssertionError):
            self.assert_exact_release_cohort(gate)
        # Also keep the old aggregate count unchanged: the ID fingerprint,
        # rather than only the count, must reject a swapped-in rejected record.
        gate.eligible_hazards.remove('H001')
        self.assertEqual(len(pre_common_gate(pre_citation_gate(gate)).eligible_hazards), 1653 + len(ADMITTED_IDS))
        with self.assertRaises(AssertionError):
            self.assert_exact_release_cohort(gate)


class CommerceCohortHelperTests(unittest.TestCase):
    def test_unknown_additions_and_unrelated_lifecycle_changes_remain_visible(self):
        self.assertEqual(pre_commerce_ids('evidence', ADDED_IDS['evidence'] | {'E_UNREVIEWED'}),
                         {'E_UNREVIEWED'})
        hid = next(iter(CANDIDATE_IDS))
        self.assertEqual(pre_commerce_inventory('hazards', [(hid, 'active'), ('H_UNRELATED', 'active')]),
                         sorted([(hid, 'proposed'), ('H_UNRELATED', 'active')]))

    def test_shared_clause_survives_when_old_link_still_uses_it(self):
        new_h = next(iter(ADMITTED_IDS))
        new_k = next(iter(ADDED_IDS['links']))
        gate = SimpleNamespace(eligible_hazards={'H_OLD', new_h, 'H_UNEXPECTED'},
                               eligible_links={'K_OLD', new_k, 'K_UNEXPECTED'},
                               links={'K_OLD': {'clauseId': 'C_SHARED'},
                                      new_k: {'clauseId': 'C_SHARED'},
                                      'K_UNEXPECTED': {'clauseId': 'C_UNEXPECTED'}})
        before = copy.deepcopy(gate)
        cohort = pre_commerce_gate(gate)
        self.assertEqual(cohort.eligible_hazards, {'H_OLD', 'H_UNEXPECTED'})
        self.assertEqual(cohort.eligible_links, {'K_OLD', 'K_UNEXPECTED'})
        self.assertEqual({cohort.links[k]['clauseId'] for k in cohort.eligible_links},
                         {'C_SHARED', 'C_UNEXPECTED'})
        self.assertEqual(vars(gate), vars(before))

    def test_manifest_projection_does_not_mutate_or_hide_an_unknown_increment(self):
        current = read(KNOW / 'manifest.json')
        before = copy.deepcopy(current)
        historical = pre_commerce_manifest(current)
        current['counts']['evidence'] += 1
        changed = pre_commerce_manifest(current)
        self.assertEqual(changed['counts']['evidence'], historical['counts']['evidence'] + 1)
        self.assertEqual(before['counts']['evidence'] - historical['counts']['evidence'], len(ADDED_IDS['evidence']) + len(CITATION_ADDED_IDS['evidence']) + len(COMMON_ADDED_IDS['evidence']))
        self.assertEqual(before, read(KNOW / 'manifest.json'))


if __name__ == '__main__':
    unittest.main()
