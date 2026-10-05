"""Original attachment fidelity and bounded construction-body publication."""
from commerce_cohort_fixture import pre_commerce_manifest
import hashlib,json,sys,unittest
from datetime import date
from pathlib import Path
from power_fixture import CLAUSES as POWER_CLAUSES, EVIDENCE as POWER_EVIDENCE, VERSION as POWER_VERSION
from coal_fixture import CLAUSES as COAL_CLAUSES, EVIDENCE as COAL_EVIDENCE, VERSION as COAL_VERSION
from construction_fixture import CLAUSES,EVIDENCE,VERSION
ROOT=Path(__file__).resolve().parents[3]
from official_clause_cohort_fixture import pre_official_repo_root
# Preserve the dated cohort against its exact, fail-closed batch predecessor.
ROOT = pre_official_repo_root(ROOT);KNOW=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools/v4'))
from major_criteria import load_config,public_projection,scope_review_bindings

def read(p):return json.loads(p.read_text(encoding='utf-8'))


class ConstructionCriteriaTests(unittest.TestCase):
    def test_exact_39_independently_reviewed_sources(self):
        f=read(ROOT/'tests/private/construction-full-criteria-source-v1.json')
        self.assertEqual(len(f['files']),39)
        for r in f['files']:
            with self.subTest(path=r['path']):self.assertEqual(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest(),r['sha256'])

    def test_original_attachment_body_and_nested_conditions_are_preserved(self):
        clauses=[read(KNOW/'clauses'/f'C_MOHURD_CONSTRUCTION_2024_{n}.json') for n in range(1,19)]
        self.assertEqual({c['id'] for c in clauses},CLAUSES)
        body='\n\n'.join(c['quote'] for c in clauses)+'\n'
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),'8b18b70858307c184d3541b44eb0153a8f3d870760a3b3722020550760a361ad')
        self.assertIn('之一，且未及时处理：\n1.',clauses[4]['quote'])
        self.assertIn('\n4.桩间土流失孔洞深度超过桩径。',clauses[4]['quote'])
        self.assertIn('且未做可靠连接',clauses[8]['quote'])
        self.assertIn('或电梯井道内贯通未采取水平防护措施且电梯井口未设置防护门',clauses[8]['quote'])
        self.assertIn('未辨识施工现场有限空间，且未在显著位置设置警示标志',clauses[10]['quote'])
        self.assertIn('未及时采取措施',clauses[12]['quote'])
        self.assertIn('且存在危害程度较大',clauses[16]['quote'])
        self.assertIn('建质规〔2022〕2号）同时废止',clauses[17]['quote'])

    def test_level_counts_do_not_add_nested_conditions_as_new_items(self):
        s=next(s for s in load_config(KNOW)['standards'] if s['lawVersionId']==VERSION)
        self.assertEqual([r['judgmentItemCount'] for r in s['clauses']],[0,0,0,5,4,4,3,9,5,2,4,2,7,3,3,1,1,0])
        self.assertEqual(s['expectedJudgmentItemCount'],53)
        self.assertIn('51个一级列项',s['officialScope']['label']);self.assertIn('不重复加总',s['officialScope']['label'])
        self.assertEqual(s['topicLinks'],[])
        review=read(KNOW/'major-criteria/v1/reviews'/(VERSION+'.json'))
        bindings,_=scope_review_bindings(s,KNOW)
        for k,v in bindings.items():self.assertEqual(review[k],v)
        self.assertEqual(read(KNOW/'evidence/E_MOHURD_CONSTRUCTION_FULL_20261001.json')['snapshotSha256'],'5397b6b88ed2921bfa5516f598866ce24a3cbbdabb2b283955d22ac7d25b32ca')

    def test_no_new_hazards_links_or_canonical_identity(self):
        self.assertEqual([read(p)['id'] for p in (KNOW/'links').glob('*.json') if read(p).get('clauseId') in CLAUSES],[])
        manifest = pre_commerce_manifest(read(KNOW/'manifest.json'));b=next(b for b in manifest['batches'] if b['id']=='construction-full-criteria-20261001')
        self.assertEqual((b['clausesAdded'],b['evidenceAdded'],b['hazardsAdded'],b['linksAdded']),(18,2,0,0))
        self.assertEqual((manifest['counts']['laws'],manifest['counts']['lawVersions'],manifest['counts']['clauses'] - len(COAL_CLAUSES) - len(POWER_CLAUSES),manifest['counts']['evidence'] - len(COAL_EVIDENCE) - len(POWER_EVIDENCE)),(119,122,3040,1294))
        self.assertEqual((manifest['counts']['hazards'],manifest['counts']['links']),(2131,1971))
        self.assertEqual(sum(read(p).get('documentNumber')=='建质规〔2024〕5号' for p in (KNOW/'law-versions').glob('*.json')),1)

    def test_actual_review_date_and_cumulative_catalog_without_hazard_inflation(self):
        old=public_projection(KNOW,as_of=date(2026,9,30));now=public_projection(KNOW,as_of=date(2026,10,1))
        self.assertEqual((len(old['catalog']['standards']),sum(len(s['clauses']) for s in old['catalog']['standards']),len(old['topic']['hazardIds'])),(2,22,19))
        prior_standards=[s for s in now['catalog']['standards'] if s['lawVersionId'] not in {COAL_VERSION, POWER_VERSION}]
        self.assertEqual((len(prior_standards),sum(len(s['clauses']) for s in prior_standards),len(now['topic']['hazardIds'])),(4,51,20))
        row=next(s for s in now['catalog']['standards'] if s['lawVersionId']==VERSION)
        self.assertEqual(row['coverage']['reviewedWholeClauseCount'],18);self.assertEqual(row['directHazardCount'],0)
        self.assertTrue(row['coverage']['wholeStandardComplete']);self.assertFalse(now['catalog']['allIndustryCoverage'])


if __name__=='__main__':unittest.main()
