"""A local fire ordinance cannot become nationwide through migrated CN codes."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3] / 'knowledge'
CLAUSE = 'C_FBF31A0937B68B9F9F6A4D0993'
LINKS = ('K_4AF820EA7AC674CE787AE161', 'K_7E30C53DFD3AB8847A72ACD0',
         'K_1538F7DDC2147E518603C8E5')


class NanjingFireScopeTests(unittest.TestCase):
    def read(self, path):
        return json.loads((ROOT / path).read_text(encoding='utf-8'))

    def test_local_clause_and_all_three_existing_links_keep_local_scope(self):
        clause = self.read('clauses/' + CLAUSE + '.json')
        self.assertEqual(clause['jurisdictionCode'], 'CN-3201')
        version = self.read('law-versions/' + clause['lawVersionId'] + '.json')
        self.assertEqual(version['scope'], 'CN-3201')
        self.assertEqual(version['officialName'], '南京市消防条例')
        for kid in LINKS:
            link = self.read('links/' + kid + '.json')
            self.assertEqual(link['clauseId'], CLAUSE)
            self.assertEqual(link['jurisdictionCode'], 'CN-3201')
            self.assertIn('限南京市行政区域', link['applicability'])
            self.assertEqual(link['role'], 'direct')

    def test_complete_scope_and_operative_article_are_supported_by_legislature(self):
        evidence = self.read('evidence/E_NANJING_FIRE_ART2_47_SCOPE_20261108.json')
        self.assertTrue(evidence['url'].startswith('https://rd.nanjing.gov.cn/'))
        quote = re.sub(r'\s+', '', evidence['completeOfficialQuote'])
        self.assertIn('本市行政区域内的消防工作和相关应急救援工作，适用本条例。', quote)
        self.assertIn('法律、法规对森林、铁路、港口（含渔业港口）', quote)
        clause = self.read('clauses/' + CLAUSE + '.json')
        self.assertIn(re.sub(r'\s+', '', clause['quote']), quote)
        self.assertIn('禁止燃放孔明灯、荷花灯', quote)

    def test_original_nationwide_migration_error_is_retained_in_history(self):
        for kind, ids in [('clauses', [CLAUSE]), ('links', LINKS)]:
            for entity_id in ids:
                review = self.read('reviews/' + kind + '/' + entity_id + '.json')
                self.assertEqual(review['previousEntity']['jurisdictionCode'], 'CN')
                self.assertEqual(review['previousReview']['entityId'], entity_id)
                self.assertFalse(review['reviewEvidence']['siteFactsVerified'])
                self.assertFalse(review['reviewEvidence']['independentProfessionalReview'])


if __name__ == '__main__':
    unittest.main()
