"""One reviewed GB12801 first-sentence successor; historical records stay intact.

The diagnostic counterexamples deliberately show why fresh hashes alone are not
semantic legal review. They are not approved data changes or migration helpers.
"""
import copy
import hashlib
import json
from datetime import date
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
from recovery_cohort_fixture import pre_recovery_repo_root
ROOT = pre_recovery_repo_root(ROOT)
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools' / 'v4'))
from canonical import content_hash
import release_gate_core as gate

OLD_H = 'H_CE94D2ACC8C544BCA0FB0AA026'
OLD_K = 'K_XLSX_WEB_' + OLD_H
NEW_H = 'H_GB12801_2025_5_6_2_S1'
NEW_K = 'K_GB12801_2025_5_6_2_S1'
NEW_V = 'LV_STD_GB12801'
OLD_V = 'LV_STD_GB12801_2008'
NEW_C = 'C_12801_5_6_2'


class BoundedTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        groups = ['laws', 'law-versions', 'clauses', 'hazards', 'links']
        cls.current = {rel: gate.load_dir(KNOW, rel) for rel in groups}
        cls.current.update({f'reviews/{rel}': gate.load_reviews(KNOW, f'reviews/{rel}')
                            for rel in groups})
        cls.baseline = copy.deepcopy(cls.current)
        cls.baseline['law-versions'][NEW_V]['validityStatus'] = 'upcoming'
        for rel, entity in [('law-versions', NEW_V), ('clauses', NEW_C)]:
            cls.baseline['reviews/' + rel][entity] = copy.deepcopy(
                cls.current['reviews/' + rel][entity]['previousReview'])
        for rel, entity in [('hazards', NEW_H), ('links', NEW_K)]:
            del cls.baseline[rel][entity]
            del cls.baseline['reviews/' + rel][entity]

    def evaluate(self, state, day):
        def read(_root, rel):
            return copy.deepcopy(state[rel.replace('\\', '/')])
        with patch.object(gate, 'load_dir', read), patch.object(gate, 'load_reviews', read):
            return gate.evaluate_release_gate(KNOW, date.fromisoformat(day))

    def test_mock_read_accepts_posix_and_windows_review_paths(self):
        for relative in ('reviews/laws', r'reviews\laws'):
            with self.subTest(path=relative):
                def evaluate(root, _day):
                    return gate.load_reviews(root, relative)
                with patch.object(gate, 'evaluate_release_gate', evaluate):
                    result = self.evaluate(self.current, '2026-10-01')
                self.assertEqual(result, self.current['reviews/laws'])
                result.clear()
                self.assertTrue(self.current['reviews/laws'])

    def test_twenty_bounded_gate_scenarios(self):
        scenarios = []

        def run(name, state, day):
            result = self.evaluate(state, day)
            scenarios.append(name)
            return result

        before = run('baseline_before', self.baseline, '2026-09-30')
        after = run('baseline_after', self.baseline, '2026-10-01')
        final_before = run('final_before', self.current, '2026-09-30')
        final_after = run('final_after', self.current, '2026-10-01')
        self.assertIn(OLD_H, before.eligible_hazards)
        self.assertIn(OLD_K, before.eligible_links)
        self.assertNotIn(OLD_H, after.eligible_hazards)
        self.assertNotIn(OLD_K, after.eligible_links)
        self.assertEqual(final_before.eligible_hazards, before.eligible_hazards)
        self.assertEqual(final_before.eligible_links, before.eligible_links)
        self.assertEqual(final_after.eligible_hazards, after.eligible_hazards | {NEW_H})
        self.assertEqual(final_after.eligible_links, after.eligible_links | {NEW_K})

        version_only = copy.deepcopy(self.baseline)
        for rel in ['law-versions', 'reviews/law-versions']:
            version_only[rel][NEW_V] = copy.deepcopy(self.current[rel][NEW_V])
        r = run('version_only', version_only, '2026-10-01')
        self.assertEqual(r.eligible_hazards, after.eligible_hazards)
        self.assertEqual(r.eligible_links, after.eligible_links)
        stale = copy.deepcopy(version_only)
        stale['reviews/law-versions'][NEW_V] = self.baseline['reviews/law-versions'][NEW_V]
        r = run('stale_version_review', stale, '2026-10-01')
        self.assertFalse(r.law_versions[NEW_V]['ok'])

        # Reusing the old IDs destroys the old-date meaning even with fresh hashes.
        reuse = copy.deepcopy(version_only)
        reused_h = {**self.current['hazards'][NEW_H], 'id': OLD_H}
        reused_k = {**self.current['links'][NEW_K], 'id': OLD_K, 'hazardId': OLD_H}
        reuse['hazards'][OLD_H] = reused_h
        reuse['links'][OLD_K] = reused_k
        reuse['reviews/hazards'][OLD_H] = {
            **self.current['reviews/hazards'][NEW_H], 'entityId': OLD_H,
            'reviewedContentHash': content_hash(reused_h)}
        reuse['reviews/links'][OLD_K] = {
            **self.current['reviews/links'][NEW_K], 'entityId': OLD_K,
            'reviewedContentHash': content_hash(reused_k),
            'contextHashes': {'hazard': content_hash(reused_h),
                              'clause': content_hash(self.current['clauses'][NEW_C])}}
        r = run('unsafe_id_reuse', reuse, '2026-09-30')
        self.assertNotIn(OLD_H, r.eligible_hazards)
        self.assertNotIn(OLD_K, r.eligible_links)

        # Documentary limitation of the structural gate, NOT semantic approval.
        swap = copy.deepcopy(reuse)
        swap['hazards'][OLD_H] = copy.deepcopy(self.baseline['hazards'][OLD_H])
        swap['reviews/hazards'][OLD_H] = copy.deepcopy(self.baseline['reviews/hazards'][OLD_H])
        swap['reviews/links'][OLD_K]['contextHashes']['hazard'] = content_hash(
            swap['hazards'][OLD_H])
        r = run('diagnostic_mechanical_swap', swap, '2026-10-01')
        self.assertIn(OLD_H, r.eligible_hazards)
        self.assertNotEqual(swap['links'][OLD_K], self.current['links'][OLD_K])

        archived = copy.deepcopy(self.current)
        archived['hazards'][OLD_H]['lifecycle'] = 'superseded'
        archived['reviews/hazards'][OLD_H]['reviewedContentHash'] = content_hash(
            archived['hazards'][OLD_H])
        r = run('unsafe_hazard_supersession', archived, '2026-09-30')
        self.assertNotIn(OLD_H, r.eligible_hazards)
        repealed = copy.deepcopy(self.current)
        repealed['law-versions'][OLD_V]['validityStatus'] = 'repealed'
        repealed['reviews/law-versions'][OLD_V]['reviewedContentHash'] = content_hash(
            repealed['law-versions'][OLD_V])
        r = run('unsafe_version_repeal', repealed, '2026-09-30')
        self.assertFalse(r.law_versions[OLD_V]['supports_current'])

        mutations = [
            ('pending_hazard', 'reviews/hazards', NEW_H, lambda x: x.update(decision='pending')),
            ('stale_hazard', 'reviews/hazards', NEW_H, lambda x: x.update(reviewedContentHash='stale')),
            ('stale_hazard_context', 'reviews/links', NEW_K,
             lambda x: x['contextHashes'].update(hazard='stale')),
            ('stale_clause_context', 'reviews/links', NEW_K,
             lambda x: x['contextHashes'].update(clause='stale')),
            ('empty_clause_evidence', 'reviews/clauses', NEW_C, lambda x: x.update(evidenceRefs=[])),
            ('pending_link', 'reviews/links', NEW_K, lambda x: x.update(decision='pending')),
            ('proposed_hazard', 'hazards', NEW_H, lambda x: x.update(lifecycle='proposed')),
        ]
        for name, rel, entity, mutate in mutations:
            with self.subTest(name=name):
                state = copy.deepcopy(self.current)
                mutate(state[rel][entity])
                r = run(name, state, '2026-10-01')
                self.assertNotIn(NEW_H, r.eligible_hazards)
        for rel, entity in [('reviews/hazards', NEW_H), ('reviews/links', NEW_K),
                            ('reviews/clauses', NEW_C)]:
            with self.subTest(missing_review=rel):
                state = copy.deepcopy(self.current)
                del state[rel][entity]
                r = run('missing_' + rel, state, '2026-10-01')
                self.assertNotIn(NEW_H, r.eligible_hazards)
        self.assertEqual(len(scenarios), 20)
        self.assertEqual(len(set(scenarios)), 20)

    def test_exact_approved_slice_and_review_dependencies(self):
        hazard = self.current['hazards'][NEW_H]
        link = self.current['links'][NEW_K]
        clause = self.current['clauses'][NEW_C]
        self.assertEqual(content_hash(hazard),
                         '3e634a5d4b5ad72f703550ffe31ce9c32fb22914bfabac79b15e2c45b39307bb')
        self.assertEqual(content_hash(link),
                         'd6a76e5ea118af3026e59016a4e2533bf832f0dc30f919c9f95380695343c3a4')
        self.assertEqual(content_hash(clause),
                         '0fac0368061bc5c85d46eb57c1a59b070bf25ba5802fe80c60acd6923821848d')
        self.assertEqual(clause['quote'],
                         '存在高处坠落危险的平台、通道或工作面,应采取防护栏杆等防坠落措施。'
                         '楼面、平台或走道的防护栏杆下部应设置踢脚板。')
        for key in ('title', 'description', 'measures', 'conditions'):
            self.assertNotIn('踢脚板', hazard[key])
            self.assertNotIn('系挂装置', hazard[key])
            self.assertNotIn('扶梯', hazard[key])
        self.assertEqual(link['clauseId'], NEW_C)
        self.assertEqual(link['hazardId'], NEW_H)
        self.assertIn('第一句', link['applicability'])
        review = self.current['reviews/links'][NEW_K]
        self.assertEqual(review['reviewedContentHash'], content_hash(link))
        self.assertEqual(review['contextHashes'],
                         {'hazard': content_hash(hazard), 'clause': content_hash(clause)})
        for rel, entity in [('law-versions', NEW_V), ('clauses', NEW_C),
                            ('hazards', NEW_H), ('links', NEW_K)]:
            review = self.current['reviews/' + rel][entity]
            self.assertEqual(review['decision'], 'verified')
            self.assertEqual(review['reviewedContentHash'], content_hash(self.current[rel][entity]))
            for eid in review['evidenceRefs']:
                evidence = json.loads((KNOW / 'evidence' / (eid + '.json')).read_text())
                self.assertEqual(evidence['tier'], 'authoritative-public')
                self.assertTrue(evidence['url'].startswith('https://'))
                self.assertEqual(len(evidence['snapshotSha256']), 64)
                if eid in {'E_GB12801_EFFECTIVE_20261001', 'E_GB12801_SCOPE_5_6_2_20261001'}:
                    self.assertEqual(evidence['snapshotSha256'],
                                     'a289896e088b594f2941342ff37fcb73f4a657c3ad96965dffd4604e1e268f0c')
                    self.assertEqual(evidence['url'],
                                     'https://xcoss.henan.gov.cn/typtfile/20260120/'
                                     '84600d71bf854522bf2aff6982cd488b.pdf')

    def test_old_definition_link_and_review_bytes_are_retained(self):
        frozen = {
            'links/K_XLSX_WEB_H_CE94D2ACC8C544BCA0FB0AA026.json': 'c153ba91d65c6959a0e725a8e5b652c72d3e6a722700c71c4c7d734ecbe7ae13',
            'clauses/C_GBT12801_5_7_1_C.json': '8e97a6d0dc5148e7c2d2a466b05aac3614202acfb3fae3d56c71e65d76e06b60',
            'reviews/clauses/C_GBT12801_5_7_1_C.json': '2020f12b9be2e3b64aa5be2b29dcbe962febca7eb88b34f0a7aee7bb83332051',
            'hazards/H_96B64979BEB2440B93F2D698E8.json': '081b6feecc37e3aa7723b576b5ce738da2e370f2b4a00dc63a8db27b1774585d',
            'reviews/hazards/H_96B64979BEB2440B93F2D698E8.json': 'ce710474d6f2c6a7b152b3a70349a1d1622495f540158d74dcbbb1030e8c9ab0',
            'hazards/' + OLD_H + '.json': '2928698405c85fec4a36d6b315d4ddb7d138d9d8d89b8e66adb064d144782090',
            'reviews/hazards/' + OLD_H + '.json': '8fee4fdc1a36590d44b51f4739ce34f8bd711583556b9421dd47302ebd690dbd',
            'reviews/links/' + OLD_K + '.json': '8e2c9372c7407eff0f0a226b1ac438586267f3b167f64f2c019c977fac1245d5',
            'law-versions/' + OLD_V + '.json': 'e6b2b26f21d675a7dd9b39b8fcb681edc9177d83cc6f976a0bc34d2e553bd2a2',
            'reviews/law-versions/' + OLD_V + '.json': '846ad77853a4b83b986d607804375c832f04e3eaf834e131791b4293133250f8',
        }
        for relative, expected in frozen.items():
            with self.subTest(path=relative):
                self.assertEqual(hashlib.sha256((KNOW / relative).read_bytes()).hexdigest(), expected)
        self.assertEqual(self.current['links'][OLD_K]['clauseId'], 'C_GBT12801_5_7_1_C')
        self.assertEqual(self.current['hazards']['H_96B64979BEB2440B93F2D698E8']['mergedInto'], OLD_H)
        self.assertIsNone(self.current['hazards'][OLD_H]['mergedInto'])

    def test_single_new_link_and_scoped_previous_reviews(self):
        clauses = {cid for cid, value in self.current['clauses'].items()
                   if value['lawVersionId'] == NEW_V}
        links = {kid for kid, value in self.current['links'].items()
                 if value['clauseId'] in clauses}
        self.assertEqual(len(clauses), 80)
        self.assertEqual(links, {NEW_K})
        for rel, entity, expected_hash in [
            ('law-versions', NEW_V, 'dba819c64b12b1f77de6afb82548377c0e1e5b830e4afd6da52ead620f65de81'),
            ('clauses', NEW_C, '555ad0653abdcc51281bd56a04424734af988e1572583f88333693067e147311'),
        ]:
            review = self.current['reviews/' + rel][entity]
            self.assertEqual(review['previousReviewFileSha256'], expected_hash)
            self.assertEqual(review['previousReview'], self.baseline['reviews/' + rel][entity])
            previous_hash = {
                NEW_V: 'c1359737c5e8b66547dcbe4b00d626d719903d8fe89cdcf2a7198c50c289d0f1',
                NEW_C: 'de26c86b08cf4a907fc65942d872533104762541871202ccb9b94cc10787e214',
            }
            self.assertEqual(content_hash(review['previousReview']), previous_hash[entity])
        self.assertEqual(self.current['law-versions'][NEW_V]['effectiveDate'], '2026-10-01')
        self.assertEqual(self.current['law-versions'][OLD_V]['endDate'], '2026-10-01')


if __name__ == '__main__':
    unittest.main()
