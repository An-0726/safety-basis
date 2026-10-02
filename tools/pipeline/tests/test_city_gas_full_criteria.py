"""Reviewed official text, scope and release boundaries for the bounded gas batch."""
from commerce_cohort_fixture import pre_commerce_manifest
import hashlib
import json
from datetime import date
from pathlib import Path
import sys
import unittest
from power_fixture import CLAUSES as POWER_CLAUSES, EVIDENCE as POWER_EVIDENCE, VERSION as POWER_VERSION
from coal_fixture import CLAUSES as COAL_CLAUSES, EVIDENCE as COAL_EVIDENCE, VERSION as COAL_VERSION
from construction_fixture import CLAUSES as CONSTRUCTION_CLAUSES, EVIDENCE as CONSTRUCTION_EVIDENCE
from city_gas_fixture import CLAUSES, EVIDENCE, VERSION

ROOT = Path(__file__).resolve().parents[3]
KNOW = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from major_criteria import public_projection, load_config, scope_review_bindings


def read(path): return json.loads(path.read_text(encoding='utf-8'))


class CityGasCriteriaTests(unittest.TestCase):
    def test_exact_independently_reviewed_25_source_files(self):
        fixture = read(ROOT / 'tests/private/city-gas-full-criteria-source-v1.json')
        self.assertEqual(len(fixture['files']), 25)
        for row in fixture['files']:
            with self.subTest(path=row['path']):
                self.assertEqual(hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest(), row['sha256'])

    def test_eleven_whole_articles_reconstruct_official_body_with_all_exceptions(self):
        clauses = [read(KNOW / 'clauses' / f'C_MOHURD_CITY_GAS_2023_{n}.json') for n in range(1, 12)]
        self.assertEqual({c['id'] for c in clauses}, CLAUSES)
        body = '\n\n'.join(c['quote'] for c in clauses) + '\n'
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),
                         '9177e3f2f0f0c3a369e6eccbcf1bf16f40a8768c7ceac79289c592d508bc04e7')
        self.assertIn('除确需穿过且已采取有效防护措施外', clauses[5]['quote'])
        self.assertTrue(clauses[8]['quote'].startswith('第九条　燃气经营者在对燃气用户进行安全检查时，发现有下列情形之一，不按规定采取书面告知用户整改等措施的，判定为重大隐患：'))
        self.assertIn('且存在危害程度较大', clauses[9]['quote'])
        self.assertIn('自发布之日起执行', clauses[10]['quote'])

    def test_selection_counts_distinguish_numbered_and_whole_article_criteria(self):
        s = next(s for s in load_config(KNOW)['standards'] if s['lawVersionId'] == VERSION)
        self.assertEqual([c['judgmentItemCount'] for c in s['clauses']], [0,0,0,5,5,3,3,1,4,1,0])
        self.assertEqual(s['expectedJudgmentItemCount'], 22)
        self.assertIn('20个列项', s['officialScope']['label'])
        self.assertIn('第八及十条各1个整条判据', s['officialScope']['label'])
        self.assertEqual(s['topicLinks'], [])
        review = read(KNOW / 'major-criteria/v1/reviews' / (VERSION + '.json'))
        binding, _ = scope_review_bindings(s, KNOW)
        for key, value in binding.items(): self.assertEqual(review[key], value)

    def test_no_hazard_or_link_is_fabricated_for_document_coverage(self):
        self.assertEqual([read(p)['id'] for p in (KNOW / 'links').glob('*.json')
                          if read(p).get('clauseId') in CLAUSES], [])
        manifest = pre_commerce_manifest(read(KNOW / 'manifest.json'))
        batch = next(b for b in manifest['batches'] if b['id'] == 'city-gas-full-criteria-20261001')
        self.assertEqual((batch['clausesAdded'],batch['evidenceAdded'],batch['hazardsAdded'],batch['linksAdded']), (11,2,0,0))
        self.assertEqual((manifest['counts']['clauses'] - len(CONSTRUCTION_CLAUSES) - len(COAL_CLAUSES) - len(POWER_CLAUSES),manifest['counts']['evidence'] - len(CONSTRUCTION_EVIDENCE) - len(COAL_EVIDENCE) - len(POWER_EVIDENCE)), (3022,1292))
        self.assertEqual((manifest['counts']['hazards'],manifest['counts']['links']), (2131,1971))

    def test_actual_review_dates_control_new_body_and_preserve_old_topic(self):
        old = public_projection(KNOW, as_of=date(2026,9,30))
        now = public_projection(KNOW, as_of=date(2026,10,1))
        self.assertEqual([s['lawVersionId'] for s in old['catalog']['standards']], ['L019','LV_STD_E7182E7A85BA6017C48B96A8'])
        self.assertEqual(len(old['topic']['hazardIds']),19)
        self.assertEqual(len(now['topic']['hazardIds']),20)
        gas = next(s for s in now['catalog']['standards'] if s['lawVersionId'] == VERSION)
        self.assertEqual((gas['coverage']['reviewedWholeClauseCount'],gas['directHazardCount']), (11,0))
        self.assertTrue(gas['coverage']['wholeStandardComplete'])
        self.assertEqual(sum(len(s['clauses']) for s in now['catalog']['standards'] if s['lawVersionId'] not in {'LV_MOHURD_CONSTRUCTION_MAJOR_2024', COAL_VERSION, POWER_VERSION}),33)
        self.assertFalse(now['catalog']['allIndustryCoverage'])
        for s in now['catalog']['standards'][:2]: self.assertFalse(s['coverage']['wholeStandardComplete'])


if __name__ == '__main__': unittest.main()
