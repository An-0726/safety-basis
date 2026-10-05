"""Bounded training, rejected-relation retirement and unchanged prior admissions."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
# Preserve the PR111 catalog and review-history assertions on its exact source.
from complete_remaining_cohort_fixture import pre_complete_repo_root
ROOT = pre_complete_repo_root(ROOT)
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate
from major_criteria import public_projection

TRAINING_H = 'H_8A733CAD776643E3B34B4D4689'
TRAINING_K = 'K_XLSX_NEW14_C8F99F5EA9DADDEDA007FCF9'
TRAINING_SCOPE = 'K_NEXT_GB16912_TRAINING_SCOPE'
RETIRED = {
    'K_b5854a5f230a891b5fe35e8c', 'K_9e6ba6262766224cc3d6e224',
    'K_d651b0312c6e6a0d36cde361', 'K_199989467c019b0789b69f66',
    'K_a6a1923c4d86007345fd7341', 'K_be5a0deab9619bd1579c758f',
    'K_d9b8087219c0a33495f14d72', 'K_XLSX_NEW14_EFD92528ABBFE27B1D100D87',
    'K_F46299168EA56F465C4FAD1D',
}
PR110_HAZARDS = {
    'H_4E5F4BB13B82457DA5377CABDF', 'H_GB51309_SELF_POWERED_PLUG',
    'H_GB12801_ACCIDENT_EXHAUST_INTERLOCK', 'H_200F007CE0EF47DFB8BE2B8618',
    'H_GBT34525_PREUSE_CHECK', 'H_GB55037_BUILDING_GAS_ALARM',
    'H_GB3836_UNUSED_ENTRY', 'H_GB3836_EX_D_MISSING_FASTENER',
}


def read(group, ident):
    return json.loads((ROOT / 'knowledge' / group / (ident + '.json')).read_text())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class NextTrainingInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = evaluate_release_gate(ROOT / 'knowledge', date(2026, 10, 5))
        cls.inventory = json.loads((ROOT / 'docs/NEXT_INVENTORY_INTEGRATION_20261005.json').read_text())

    def test_training_complete_clause_and_scope_are_exact(self):
        clause = read('clauses', 'C_GB16912_2008_4_13_2')
        self.assertEqual(clause['quote'], '应对员工进行安全生产技术专业培训和劳动纪律教育，经考试合格后，持证上岗。')
        self.assertEqual(clause['articlePath'], '第4.13.2条')
        self.assertEqual(clause['lawVersionId'], 'LV_STD_GB16912_2008')
        scope = read('clauses', 'C_GB16912_2008_1')
        self.assertEqual(scope['quote'], '本规程规定了工业氧气及相关气体的生产（含设计、制造、安装、改造、维修）、储存、输配和使用中应遵守的安全要求。\n本规程适用于新建、扩建和改建的采用深度冷冻法生产氧气及相关气体的单位。')
        v = read('law-versions', clause['lawVersionId'])
        self.assertEqual(v['effectiveDate'], '2009-10-01')
        self.assertEqual(v['level'], '国家标准（部分条文强制）')

    def test_training_is_recommended_bounded_and_does_not_invent_certificate_type(self):
        h, k, scope = read('hazards', TRAINING_H), read('links', TRAINING_K), read('links', TRAINING_SCOPE)
        self.assertEqual(k['clauseId'], 'C_GB16912_2008_4_13_2')
        self.assertEqual(k['role'], 'direct')
        self.assertEqual(scope['clauseId'], 'C_GB16912_2008_1')
        self.assertEqual(scope['role'], 'supporting')
        for obj, field in ((h, 'conditions'), (k, 'applicability'), (scope, 'applicability')):
            for token in ('新建、扩建和改建', '采用深度冷冻法生产氧气及相关气体',
                          '第4.13.2不在前言强制条文清单中', '推荐性技术要求',
                          '不单独认定行政违法或重大事故隐患', '未规定证件名称、发证机关或法定资格类型',
                          '不得由本条推导所有行业所有员工必须取得特种作业证',
                          '一般氧气购买、使用场所', '不得仅因未出示资料推定未培训或考试不合格'):
                self.assertIn(token, obj[field])
        self.assertIn('另按该岗位真正适用的资格规定核查', h['measures'])
        self.assertIn(TRAINING_H, self.gate.eligible_hazards)
        self.assertTrue({TRAINING_K, TRAINING_SCOPE} <= self.gate.eligible_links)
        topic = public_projection(ROOT / 'knowledge', as_of=date(2026, 10, 5))['topic']
        self.assertNotIn(TRAINING_H, topic['hazardIds'])

    def test_training_current_bindings_and_complete_previous_definitions_are_preserved(self):
        for group, ident in [('laws', 'LF_STD_GB16912'), ('law-versions', 'LV_STD_GB16912_2008'),
                             ('clauses', 'C_GB16912_2008_1'), ('clauses', 'C_GB16912_2008_4_13_2'),
                             ('hazards', TRAINING_H), ('links', TRAINING_K), ('links', TRAINING_SCOPE)]:
            entity, review = read(group, ident), read('reviews/' + group, ident)
            self.assertEqual(review['decision'], 'verified')
            self.assertEqual(review['reviewedContentHash'], content_hash(entity))
            self.assertIn('E_NEXT_GB16912_TRAINING_20261005', review['evidenceRefs'])
            if group == 'links':
                self.assertEqual(review['contextHashes'], {'hazard': content_hash(read('hazards', TRAINING_H)),
                    'clause': content_hash(read('clauses', entity['clauseId']))})
        for group, ident in [('hazards', TRAINING_H), ('links', TRAINING_K)]:
            review = read('reviews/' + group, ident)
            self.assertEqual(review['previousDefinition']['id'], ident)
            self.assertTrue(review['previousReview'])
        self.assertEqual(read('reviews/links', TRAINING_K)['previousDefinition']['clauseId'], 'C_XLSX_FT_21B1419C81F55761621AAEBD')

    def test_nine_retired_relations_remain_rejected_and_keep_exact_previous_records(self):
        rows = {r['entityId']: r for r in self.inventory['decisions'] if r['action'] == 'retire_rejected_relation'}
        self.assertEqual(set(rows), RETIRED)
        for kid, row in rows.items():
            with self.subTest(link=kid):
                entity, review = read('links', kid), read('reviews/links', kid)
                before = json.loads(row['beforeEntityFileText'])
                self.assertEqual(entity, {**before, 'lifecycle': 'superseded'})
                self.assertFalse(row['legalAdmissionChanged'])
                self.assertEqual(review['decision'], 'rejected')
                self.assertEqual(review['reviewedContentHash'], content_hash(entity))
                self.assertEqual(review['previousDefinition'], before)
                self.assertEqual(review['previousReview'], json.loads(row['beforeReviewFileText']))
                self.assertEqual(review['previousEntityFileSha256'], sha(row['beforeEntityFileText'].encode()))
                self.assertEqual(review['previousReviewFileSha256'], sha(row['beforeReviewFileText'].encode()))
                self.assertEqual(review['contextHashes'], {'hazard': content_hash(read('hazards', entity['hazardId'])),
                    'clause': content_hash(read('clauses', entity['clauseId']))})
                self.assertNotIn(kid, self.gate.eligible_links)

    def test_product_standard_candidate_state_changes_do_not_approve_its_claim(self):
        h, k = 'H_BC2436C8E5BE198BA82BB74B82_1', 'K_XLSX_FT_80C4D8363ED159B6CC323D7C'
        for group, ident in [('hazards', h), ('links', k)]:
            entity, review = read(group, ident), read('reviews/' + group, ident)
            row = next(r for r in self.inventory['decisions'] if r['entityId'] == ident)
            before = json.loads(row['beforeEntityFileText'])
            changes = {'lifecycle': 'proposed'}
            if group == 'hazards': changes['mode'] = 'candidate'
            self.assertEqual(entity, {**before, **changes})
            self.assertIn(review['decision'], {'pending', 'rejected'})
            self.assertEqual(review['reviewedContentHash'], content_hash(entity))
            self.assertEqual(review['previousDefinition'], before)
            self.assertEqual(review['previousReview'], json.loads(row['beforeReviewFileText']))
        self.assertNotIn(h, self.gate.eligible_hazards)
        self.assertNotIn(k, self.gate.eligible_links)

    def test_major_catalog_changes_only_the_obsolete_aq7011_candidate_relation(self):
        correction = self.inventory['majorPendingCorrection']
        self.assertEqual(sha(correction['beforeCatalogFileText'].encode()), correction['beforeCatalogFileSha256'])
        before = json.loads(correction['beforeCatalogFileText'])
        expected = copy.deepcopy(before)
        removed = [{'linkId': 'K_XLSX_WEB_H_B0B7C75B5F0D423386A84AB73D',
                    'hazardId': 'H_B0B7C75B5F0D423386A84AB73D', 'clauseId': 'C_MEM10_4_2'}]
        self.assertEqual(correction['removedRows'], removed)
        standard = next(s for s in expected['standards'] if s['lawVersionId'] == 'L019')
        for row in removed: standard['pendingTopicLinks'].remove(row)
        self.assertEqual(json.loads((ROOT / 'knowledge/major-criteria/v1/catalog.json').read_text()), expected)
        self.assertEqual({r['hazardId'] for r in standard['pendingTopicLinks']},
                         {'H_68196C0A0FBDDAF0354E0F71', 'H_B552B08A4FD28A8770CDC2BB'})

    def test_historical_gb12801_relation_is_kept_and_respects_its_end_date(self):
        h = 'H_CE94D2ACC8C544BCA0FB0AA026'; k = 'K_XLSX_WEB_' + h
        self.assertEqual(read('hazards', h)['lifecycle'], 'active')
        self.assertEqual(read('links', k)['lifecycle'], 'active')
        self.assertEqual(read('links', k)['clauseId'], 'C_GBT12801_5_7_1_C')
        for day, admitted in [('2026-09-30', True), ('2026-10-01', False), ('2026-10-05', False)]:
            gate = evaluate_release_gate(ROOT / 'knowledge', date.fromisoformat(day))
            with self.subTest(day=day):
                self.assertEqual(h in gate.eligible_hazards, admitted)
                self.assertEqual(k in gate.eligible_links, admitted)

    def test_previous_eight_official_rules_and_all_113_knowledge_records_are_untouched(self):
        old = json.loads((ROOT / 'tools/pipeline/tests/fixtures/official_clause_cohort_20261005.json').read_text())
        paths = {p: row for p, row in old['records'].items() if p.startswith('knowledge/') and p != 'knowledge/manifest.json'}
        self.assertEqual(len(paths), 113)
        for path, row in paths.items():
            with self.subTest(path=path): self.assertEqual(sha((ROOT / path).read_bytes()), row['afterSha256'])
        self.assertTrue(PR110_HAZARDS <= self.gate.eligible_hazards)


if __name__ == '__main__':
    unittest.main()
