"""Pin the 2026-09-30 incident containment without deleting canonical sources."""
from collections import Counter
from datetime import date
from commerce_cohort_fixture import pre_commerce_gate, pre_commerce_inventory, pre_commerce_ids
from common_hazards_fixture import ADDED_IDS as COMMON_ADDED_IDS
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate

# Quarantined source bytes stay intact until exact-source correction is reviewed.
# These are canonical hashes observed before this containment, not new approvals.
FROZEN = {
    'H_12158_10_1_2': ('0e8a0d83530361b03f09dec30dee440b595adb54017b2e913d52d26fef6f3cc3',
                     '6fe472607b6127e80672c791336c78a9786345111e838617dbebb684511a08bf'),
    'H_12158_4_2_3_5_2': ('f33f1aa78dfb49ade47151f54ce31dabeb5e3eddb483429e301340e8f846d254',
                         '831fff7db5b47c739f5c2ccca88562d506f24b175a92369c80cd61819a2f86ea'),
    'H_12158_6_3_1_1': ('71ac75c08efdc5807b2f7e073efd598346a2676fc19065666c498b90398ca64b',
                       '7034dea0c986d3d798dea0fee0ee3a6d91a7b2c7cc4f358d6cdd67e72e4d7590'),
    'H_12158_6_3_2_2': ('8679cb03a293b1da93d352288ba249c743f68dfa82d1e5476c4126e7a3abb6ce',
                       'aa6ec231a5995d09934c0fb5440107e0fa0d50f4e6f0f6ed0f94f240f108484e'),
    'H_12158_7_6_1': ('c7c2761cbcd69cb18eddfbc54518d6f3c943aa335ce712761580c171a71e28cc',
                     'cdc55d089f4dc573009859fddc1b66172d90bb795fdcddddb3ac1f3983b52108'),
    'H_12158_8_8_5_3': ('2818557f79c8dba3c2a894de7ac8fbcc77b709cb88c4775226889f35a9a95d9b',
                       'efd86b41114d5b65b883e0f299f65076173fbcf9633c2bfd880dd6d12c2ae834'),
}
MEASURES = ('立即停止安排未成年工从事接触职业病危害的作业；对有职业禁忌的劳动者，'
            '调整至不涉及其所禁忌作业的岗位。结合劳动者年龄、职业健康检查结论与岗位危害核查用工安排，'
            '保留岗位调整及复核记录；不得以配发个人防护用品替代上述岗位安排限制。')
EVIDENCE = 'E_NHC_WORKPLACE_OH_20260930'


def read(rel):
    return json.loads((KNOW / rel).read_text(encoding='utf-8'))


class SourceIntegrityContainmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = evaluate_release_gate(KNOW, date(2026, 9, 30))

    def test_six_entities_and_contexts_are_preserved_but_reviews_are_rejected(self):
        for hid, (hazard_hash, link_hash) in FROZEN.items():
            with self.subTest(hazard=hid):
                kid = 'K_XLSX_WEB_' + hid
                hazard = read(f'hazards/{hid}.json')
                link = read(f'links/{kid}.json')
                hr = read(f'reviews/hazards/{hid}.json')
                kr = read(f'reviews/links/{kid}.json')
                self.assertEqual(hazard['id'], hid)
                self.assertEqual(link['id'], kid)
                self.assertEqual(hazard['lifecycle'], 'active')
                self.assertEqual(link['lifecycle'], 'active')
                self.assertEqual(content_hash(hazard), hazard_hash)
                self.assertEqual(content_hash(link), link_hash)
                self.assertEqual(hr['decision'], 'rejected')
                self.assertEqual(kr['decision'], 'rejected')
                self.assertEqual(hr['reviewedContentHash'], hazard_hash)
                self.assertEqual(kr['reviewedContentHash'], link_hash)
                self.assertEqual(kr['contextHashes']['hazard'], hazard_hash)
                self.assertEqual(kr['contextHashes']['clause'],
                                 content_hash(read(f"clauses/{link['clauseId']}.json")))
                self.assertIn('重新', hr['reason'])
                self.assertIn('重新', kr['reason'])

    def test_rejected_six_cannot_enter_dated_public_chain(self):
        for hid in FROZEN:
            self.assertNotIn(hid, self.gate.eligible_hazards)
            self.assertNotIn('K_XLSX_WEB_' + hid, self.gate.eligible_links)
            self.assertEqual(self.gate.hazards[hid]['reasons'],
                             ['BLOCK_REVIEW_NOT_VERIFIED:rejected'])
        # Current projection additionally excludes four MEM10 wrong-source chains;
        # the separate containment suite verifies exact historical count recovery.
        cohort = pre_commerce_gate(self.gate)
        self.assertEqual(len(cohort.eligible_hazards), 1653)
        self.assertEqual(len(cohort.eligible_links), 1787)
        self.assertEqual(len({cohort.links[k]['clauseId'] for k in cohort.eligible_links}), 1338)

    def test_corrupt_formula_clause_is_preserved_and_not_publishable(self):
        clause = read('clauses/C_12158_2.json')
        review = read('reviews/clauses/C_12158_2.json')
        self.assertEqual(content_hash(clause),
                         '2f3cdc1dd4be2dce00a22524e8ae87b4fdde3603bd2e50c9d9bfe30b7c3f8fac')
        self.assertEqual(clause['lifecycle'], 'active')
        self.assertEqual(review['decision'], 'rejected')
        self.assertEqual(review['reviewedContentHash'], content_hash(clause))
        self.assertFalse(self.gate.clauses[clause['id']]['ok'])
        self.assertNotIn(clause['id'], {self.gate.links[k]['clauseId']
                                       for k in self.gate.eligible_links})

    def test_corrected_occupational_measures_are_bound_after_substantive_review(self):
        hid = 'H_ZJWS_33_1'
        kid = 'K_XLSX_FT_E94F0A28CBE0F9F58B3750D8'
        h, k = read(f'hazards/{hid}.json'), read(f'links/{kid}.json')
        hr, kr = read(f'reviews/hazards/{hid}.json'), read(f'reviews/links/{kid}.json')
        self.assertEqual(h['measures'], MEASURES)
        self.assertEqual(h['lifecycle'], 'active')
        self.assertEqual(content_hash(k),
                         'aeff90030c84d9ef0d572fca70d38cda0ea823aeed8fd948038bcda7bb857002')
        self.assertEqual(hr['reviewedContentHash'], content_hash(h))
        self.assertEqual(kr['reviewedContentHash'], content_hash(k))
        self.assertEqual(kr['contextHashes']['hazard'], content_hash(h))
        self.assertEqual(kr['contextHashes']['clause'],
                         'a31ba257fac116fddd8c5f953b95064850f8a084d1746d31e4a402b08b7097fa')
        for review in (hr, kr):
            self.assertEqual(review['decision'], 'verified')
            self.assertIn(EVIDENCE, review['evidenceRefs'])
            self.assertTrue(review['checkedAt'].startswith('2026-09-30'))
            self.assertIn('第三十三条', review['reason'])
        self.assertIn(hid, self.gate.eligible_hazards)
        self.assertIn(kid, self.gate.eligible_links)

    def test_official_evidence_is_dated_scoped_and_manifest_is_reconciled(self):
        e = read(f'evidence/{EVIDENCE}.json')
        self.assertEqual(e['id'], EVIDENCE)
        self.assertEqual(e['tier'], 'authoritative-public')
        self.assertEqual(e['url'], 'https://www.nhc.gov.cn/wjw/c100221/202201/edc9ae24435d4d93ace796f33c29b029.shtml')
        self.assertEqual(e['currentIndexUrl'], 'https://www.nhc.gov.cn/wjw/c100221/fg_gzk.shtml')
        self.assertIn('不是完整网页/PDF哈希', e['notes'])
        m = read('manifest.json')
        self.assertEqual(m['counts']['evidence'], m['evidence'])
        self.assertEqual(m['evidence'], len(list((KNOW / 'evidence').glob('*.json'))))
        hazards = [json.loads(p.read_text(encoding='utf-8')) for p in (KNOW / 'hazards').glob('*.json')]
        lifecycle = Counter(h['lifecycle'] for h in hazards)
        # Original containment inventory remains unchanged; only the separately
        # reviewed first-sentence GB12801 successor is a later addition.
        successor = [h for h in hazards if h['id'] == 'H_GB12801_2025_5_6_2_S1']
        self.assertEqual(len(successor), 1)
        self.assertEqual(successor[0]['lifecycle'], 'active')
        historical = [h for h in hazards if h['id'] != 'H_GB12801_2025_5_6_2_S1']
        historical_ids = pre_commerce_ids('hazards', {h['id'] for h in historical})
        self.assertEqual(len(historical_ids), 2130)
        # Only the pinned commerce and common-hazard additions are projected away;
        # an unknown new ID still fails this exact-set assertion.
        self.assertEqual({h['id'] for h in historical} - historical_ids,
                         {'H_COM_MOBILE_ELECTRIC_CORD_SELECTION'} | COMMON_ADDED_IDS['hazards'])
        historical_rows = pre_commerce_inventory('hazards',
            ((h['id'], h['lifecycle']) for h in historical))
        self.assertEqual(Counter(lifecycle for _, lifecycle in historical_rows),
                         {'active': 1663, 'proposed': 354, 'superseded': 113})
        historical_all = pre_commerce_inventory('hazards',
            ((h['id'], h['lifecycle']) for h in hazards))
        self.assertEqual(Counter(lifecycle for _, lifecycle in historical_all),
                         {'active': 1664, 'proposed': 354, 'superseded': 113})
        self.assertEqual(m['lifecycle'], lifecycle)


if __name__ == '__main__':
    unittest.main()
