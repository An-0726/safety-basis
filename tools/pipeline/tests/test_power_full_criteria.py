"""All power determination clauses with complete definitions and an explicit appendix boundary."""
import hashlib,json,sys,unittest
from datetime import date
from pathlib import Path
from power_fixture import CLAUSES,EVIDENCE,VERSION
ROOT=Path(__file__).resolve().parents[3];KNOW=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools/v4'))
from major_criteria import load_config,public_projection,scope_review_bindings,SCOPE_REVIEW

def read(p):return json.loads(p.read_text(encoding='utf-8'))

class PowerCriteriaTests(unittest.TestCase):
    def test_exact_81_independently_reviewed_sources(self):
        f=read(ROOT/'tests/private/power-full-criteria-source-v1.json')
        self.assertEqual(len(f['files']),81)
        for r in f['files']:
            with self.subTest(path=r['path']):self.assertEqual(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest(),r['sha256'])

    def test_all_38_article_texts_retain_numbers_common_scope_and_exceptions(self):
        cs=[read(KNOW/'clauses'/f'C_NDRC_POWER_2026_{n}.json') for n in range(1,39)]
        self.assertEqual({c['id'] for c in cs},CLAUSES)
        body='\n\n'.join(c['quote'] for c in cs)+'\n'
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),'242697477ea3ef392180f8f04c8b5979f677cd6b9a5659699db0e95f5370bc15')
        self.assertIn('危险化学品、消防（火灾）、特种设备',cs[2]['quote'])
        self.assertIn('直流±800千伏、交流1000千伏以上',cs[4]['quote'])
        for v in ('0.003L','0.002L','10‰','15‰','20‰','且未采取有效治理措施'):self.assertIn(v,cs[4]['quote'])
        self.assertIn('单套容量200兆瓦以上',cs[5]['quote']);self.assertIn('单机容量300兆瓦以上',cs[5]['quote'])
        self.assertIn('常规岛部分',cs[5]['quote']);self.assertIn('严密性均不合格',cs[5]['quote'])
        self.assertIn('经评估可能导致',cs[6]['quote']);self.assertIn('经过分析论证',cs[7]['quote'])
        self.assertIn('且无可靠应急电源',cs[7]['quote'])
        self.assertIn('或可能导致大面积停电',cs[13]['quote'])
        self.assertEqual(cs[34]['quote'],'第三十五条  本规定“以上”“超过”含本数，“以下”不含本数。')
        self.assertIn('为主营业务的企业',cs[35]['quote']);self.assertIn('国家能源局监督管理范围内水电站',cs[35]['quote'])
        self.assertIn('2026年7月1日',cs[37]['quote'])
        self.assertNotIn('同时废止',cs[37]['quote'])

    def test_determination_count_excludes_governance_and_report_form(self):
        s=next(s for s in load_config(KNOW)['standards'] if s['lawVersionId']==VERSION)
        self.assertEqual([r['judgmentItemCount'] for r in s['clauses']],[0,0,0,0,10,5,5,4,4,8,5,3,4,1]+[0]*24)
        self.assertEqual(s['expectedJudgmentItemCount'],49);self.assertFalse(s['officialScope']['wholeStandardComplete'])
        self.assertIn('附件重大隐患信息报告单',s['officialScope']['label']);self.assertIn('未声称整部文件完整',s['officialScope']['label'])
        self.assertIn('第三十五条',s['officialScope']['label']);self.assertIn('第三十六条',s['officialScope']['label'])
        self.assertEqual(s['topicLinks'],[])
        review=read(KNOW/'major-criteria/v1/reviews'/(VERSION+'.json'));bindings,deps=scope_review_bindings(s,KNOW)
        self.assertEqual(review['reviewScope'],SCOPE_REVIEW)
        for k,v in bindings.items():self.assertEqual(review[k],v)
        for eid in EVIDENCE:self.assertIn('evidence/'+eid,deps)
        self.assertEqual(read(KNOW/'evidence/E_NDRC_POWER_FULL_20261001.json')['snapshotSha256'],'20ecca5c210a1623e346ac08e62adf492134837049b1a6d6a6e2de8da8ff5548')

    def test_old_version_repeal_has_its_own_official_evidence_without_invented_date(self):
        e=read(KNOW/'evidence/E_NDRC_POWER_REPEAL_20261001.json')
        self.assertEqual(e['url'],'https://www.nea.gov.cn/20260914/cf012a88d0fa4297b6219b506bc72ed0/c.html')
        self.assertIn('附件1序号15',e['locator']);self.assertIn('不据此推定旧文2026-07-01废止或116号整体废止',e['locator'])
        self.assertEqual(read(KNOW/'law-versions'/f'{VERSION}.json')['endDate'],'')
        self.assertEqual(sorted(read(p)['id'] for p in (KNOW/'clauses').glob('*.json') if read(p).get('lawVersionId')==VERSION),sorted(CLAUSES))

    def test_no_hazard_link_or_canonical_identity_inflation(self):
        self.assertEqual([read(p)['id'] for p in (KNOW/'links').glob('*.json') if read(p).get('clauseId') in CLAUSES],[])
        m=read(KNOW/'manifest.json');b=next(b for b in m['batches'] if b['id']=='power-full-criteria-20261001')
        self.assertEqual((b['clausesAdded'],b['evidenceAdded'],b['hazardsAdded'],b['linksAdded']),(38,4,0,0))
        self.assertEqual((m['counts']['laws'],m['counts']['lawVersions'],m['counts']['clauses'],m['counts']['evidence']),(119,122,3099,1306))
        self.assertEqual((m['counts']['hazards'],m['counts']['links']),(2131,1971))
        self.assertEqual(sum(read(p).get('lawId')=='LF_NDRC_POWER_MAJOR' for p in (KNOW/'law-versions').glob('*.json')),1)

    def test_actual_review_date_projection_keeps_appendix_gap_and_hazards_separate(self):
        old=public_projection(KNOW,as_of=date(2026,9,30));now=public_projection(KNOW,as_of=date(2026,10,1))
        self.assertEqual((len(old['catalog']['standards']),sum(len(s['clauses']) for s in old['catalog']['standards']),len(old['topic']['hazardIds'])),(2,22,19))
        self.assertEqual((len(now['catalog']['standards']),sum(len(s['clauses']) for s in now['catalog']['standards']),len(now['topic']['hazardIds'])),(6,110,20))
        row=next(s for s in now['catalog']['standards'] if s['lawVersionId']==VERSION)
        self.assertEqual((row['coverage']['reviewedWholeClauseCount'],row['coverage']['reviewedJudgmentItemCount'],row['directHazardCount']),(38,49,0))
        self.assertEqual(row['coverage']['status'],'reviewed_scope_complete')
        self.assertFalse(row['coverage']['wholeStandardComplete']);self.assertFalse(now['catalog']['allIndustryCoverage'])
        self.assertNotIn('contentParts',json.dumps(row));self.assertNotIn('reviewer',json.dumps(row))

if __name__=='__main__':unittest.main()
