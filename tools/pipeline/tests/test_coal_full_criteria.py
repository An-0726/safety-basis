"""Exact official coal body, embedded tables, and separately reviewed clarifications."""
from commerce_cohort_fixture import pre_commerce_manifest
import hashlib,json,sys,unittest
from datetime import date
from pathlib import Path
from power_fixture import CLAUSES as POWER_CLAUSES, EVIDENCE as POWER_EVIDENCE, VERSION as POWER_VERSION
from coal_fixture import CLAUSES,EVIDENCE,VERSION
ROOT=Path(__file__).resolve().parents[3]
from official_clause_cohort_fixture import pre_official_repo_root
# Preserve the dated cohort against its exact, fail-closed batch predecessor.
ROOT = pre_official_repo_root(ROOT);KNOW=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools/v4'))
from major_criteria import load_config,public_projection,scope_review_bindings,RICH_SCOPE_REVIEW
from normative_content import validate_clause_content

def read(p):return json.loads(p.read_text(encoding='utf-8'))

class CoalCriteriaTests(unittest.TestCase):
    def test_exact_51_independently_reviewed_sources(self):
        f=read(ROOT/'tests/private/coal-full-criteria-source-v1.json')
        self.assertEqual(len(f['files']),51)
        for r in f['files']:
            with self.subTest(path=r['path']):self.assertEqual(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest(),r['sha256'])

    def test_complete_body_thresholds_exceptions_and_seven_tables(self):
        cs=[read(KNOW/'clauses'/f'C_MEM_COAL_2026_{n}.json') for n in range(1,22)]
        self.assertEqual({c['id'] for c in cs},CLAUSES)
        body='\n\n'.join(c['quote'] for c in cs)+'\n'
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),'aed1a34260c0b71b6bac7cd221906b761c436400f5836116bafcc6117ef1e2bb')
        self.assertIn('110%',cs[3]['quote']);self.assertIn('30%',cs[3]['quote'])
        self.assertIn('达到3.0%以上且持续时长超过10min(停电停风及打钻喷孔除外)',cs[4]['quote'])
        self.assertIn('2kW·h以上电量锂电池在井下充电时',cs[19]['quote'])
        self.assertIn('未实现独立通风，未设置具备超限自动断电功能',cs[19]['quote'])
        self.assertIn('停工〈停风〉',body);self.assertIn('煤〈岩〉柱',body)
        self.assertEqual(validate_clause_content(cs[4],[f'T_COAL_2026_{n}' for n in (1,2,3)]),[f'T_COAL_2026_{n}' for n in (1,2,3)])
        self.assertEqual(validate_clause_content(cs[5],[f'T_COAL_2026_{n}' for n in (4,5,6,7)]),[f'T_COAL_2026_{n}' for n in (4,5,6,7)])
        tables=[p for c in cs for p in c.get('contentParts',[]) if p['type']=='table']
        self.assertEqual([len(t['bodyRows']) for t in tables],[7,6,7,2,2,1,1])
        self.assertEqual(tables[1]['sourcePages'],[4,5]);self.assertEqual(tables[1]['bodyRows'][-1][1]['text'],'≥70')
        self.assertEqual(tables[3]['bodyRows'][1][0]['colSpan'],2)
        self.assertEqual(tables[5]['headerRows'][0][-1]['colSpan'],2)
        self.assertEqual(tables[6]['headerRows'][0][0]['rowSpan'],2)

    def test_level_counts_and_explicit_scope_bindings(self):
        s=next(s for s in load_config(KNOW)['standards'] if s['lawVersionId']==VERSION)
        self.assertEqual([r['judgmentItemCount'] for r in s['clauses']],[0,0,0,3,9,6,5,17,3,16,9,3,6,8,4,3,3,7,2,19,0])
        self.assertEqual(s['expectedJudgmentItemCount'],123);self.assertIn('一级列项',s['officialScope']['label'])
        self.assertEqual(s['topicLinks'],[]);self.assertEqual(len(s['applicationNotes']),7)
        review=read(KNOW/'major-criteria/v1/reviews'/(VERSION+'.json'));bindings,deps=scope_review_bindings(s,KNOW)
        self.assertEqual(review['reviewScope'],RICH_SCOPE_REVIEW)
        for k,v in bindings.items():self.assertEqual(review[k],v)
        for eid in EVIDENCE:self.assertIn('evidence/'+eid,deps)
        self.assertEqual(read(KNOW/'evidence/E_MEM_COAL_FULL_20261001.json')['snapshotSha256'],'5d08357eb7c13e31e872fc3346b43c2e20db9ddc16419bc3a3404aec23a467e5')

    def test_clarifications_do_not_overwrite_normative_text(self):
        s=next(s for s in load_config(KNOW)['standards'] if s['lawVersionId']==VERSION)
        by={n['evidenceId']:n for n in s['applicationNotes']}
        self.assertIn('井工煤矿',by['E_MEM_COAL_CLARIFICATION_1_20261001']['summary'])
        self.assertIn('纳入煤矿安全标志管理',by['E_MEM_COAL_CLARIFICATION_2_20261001']['summary'])
        battery=by['E_MEM_COAL_CLARIFICATION_3_20261001']['summary']
        for term in ('防爆柴油机无轨胶轮车','自身装配','用于车辆启动','不具备外部充电条件'):self.assertIn(term,battery)
        belt=by['E_MEM_COAL_CLARIFICATION_5_20261001']['summary']
        for term in ('机头、机尾两组','10–20m','反向风流','卸载滚筒','改向滚筒'):self.assertIn(term,belt)
        self.assertIn('所有巷道',by['E_MEM_COAL_CLARIFICATION_6_20261001']['summary'])
        self.assertIn('封闭列举',by['E_MEM_COAL_CLARIFICATION_7_20261001']['summary'])
        self.assertNotIn('不具备外部充电条件',read(KNOW/'clauses/C_MEM_COAL_2026_20.json')['quote'])

    def test_no_hazard_link_or_identity_inflation(self):
        self.assertEqual([read(p)['id'] for p in (KNOW/'links').glob('*.json') if read(p).get('clauseId') in CLAUSES],[])
        m = pre_commerce_manifest(read(KNOW/'manifest.json'));b=next(b for b in m['batches'] if b['id']=='coal-full-criteria-20261001')
        self.assertEqual((b['clausesAdded'],b['evidenceAdded'],b['hazardsAdded'],b['linksAdded']),(21,8,0,0))
        self.assertEqual((m['counts']['laws'],m['counts']['lawVersions'],m['counts']['clauses'] - len(POWER_CLAUSES),m['counts']['evidence'] - len(POWER_EVIDENCE)),(119,122,3061,1302))
        self.assertEqual((m['counts']['hazards'],m['counts']['links']),(2131,1971))
        self.assertEqual(sum(read(p).get('lawId')=='LF_MEM_COAL_MAJOR' for p in (KNOW/'law-versions').glob('*.json')),1)

    def test_true_review_dates_and_cumulative_projection(self):
        old=public_projection(KNOW,as_of=date(2026,9,30));now=public_projection(KNOW,as_of=date(2026,10,1))
        self.assertEqual((len(old['catalog']['standards']),sum(len(s['clauses']) for s in old['catalog']['standards']),len(old['topic']['hazardIds'])),(2,22,19))
        prior_standards=[s for s in now['catalog']['standards'] if s['lawVersionId'] != POWER_VERSION]
        self.assertEqual((len(prior_standards),sum(len(s['clauses']) for s in prior_standards),len(now['topic']['hazardIds'])),(5,72,20))
        row=next(s for s in now['catalog']['standards'] if s['lawVersionId']==VERSION)
        self.assertEqual((row['coverage']['reviewedWholeClauseCount'],row['coverage']['reviewedTableCount'],row['coverage']['expectedTableCount'],row['directHazardCount']),(21,7,7,0))
        self.assertTrue(row['coverage']['wholeStandardComplete']);self.assertFalse(now['catalog']['allIndustryCoverage'])
        notes=[n for c in row['clauses'] for n in c.get('applicationNotes',[])]
        self.assertEqual(len(notes),7)
        self.assertTrue(all(n['isOfficialNormText'] is False for n in notes))
        self.assertNotIn('evidenceId',json.dumps(row));self.assertNotIn('snapshotSha256',json.dumps(row))

if __name__=='__main__':unittest.main()
