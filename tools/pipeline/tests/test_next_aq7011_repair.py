"""Bounded AQ7011 repair: precise annual sling inspection, never a major finding."""
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate
from major_criteria import public_projection
H='H_B0B7C75B5F0D423386A84AB73D';K='K_XLSX_WEB_'+H
C='C_NEXT_AQ7011_2018_4_6_20261005';LV='LV_STD_AQ7011_2018';LF='LF_STD_AQ7011'
def read(group,i):return json.loads((ROOT/'knowledge'/group/(i+'.json')).read_text())
class NextAq7011RepairTests(unittest.TestCase):
 def test_identity_dates_and_verified_actual_official_original(self):
  v=read('law-versions',LV);self.assertEqual(v['lawId'],LF)
  self.assertEqual(v['effectiveDate'],'2018-12-01');self.assertEqual(v['publicationDate'],'2018-05-22');self.assertEqual(v['validityStatus'],'active')
  e=read('evidence','E_NEXT_AQ7011_ORIGINAL_20261005');self.assertEqual(e['snapshotSha256'],'38b8eba427259bba4659b21ac9eb618f77b65f0352757aab6a2fa6d9c38ae203')
  self.assertEqual(e['url'],'https://hbba.sacinfo.org.cn/portal/download/e3056cdf09e44e9b7008322460c0e882');self.assertIn('PDF6/印刷2',e['locator'])
 def test_full_clause_and_conditional_branches_are_preserved(self):
  c=read('clauses',C);self.assertEqual(c['articlePath'],'第4.6条');self.assertEqual(c['lawVersionId'],LV)
  self.assertEqual(c['quote'],'起重机械应按照GB/T 6067.1和特种设备安全监督管理的有关规定定期进行检测检验。吊钩、板钩、横梁等吊具部件应每年至少进行一次离线探伤检查；吊钩、板钩等出现严重磨损、钩片开片等情况应进行更换，并对板钩、横梁的轴进行探伤检查；必要时进行金相检查，防止发生蠕变现象。')
 def test_only_narrow_inspection_branch_not_vague_machine_compliance(self):
  h=read('hazards',H);k=read('links',K)
  self.assertEqual(k['clauseId'],C);self.assertEqual(k['role'],'direct');self.assertEqual(h['id'],H)
  self.assertNotIn('不符合要求',h['title']);self.assertNotIn('销轴',h['description']);self.assertNotIn('焊缝',h['description'])
  for token in ['金属冶炼企业','高温熔融金属及熔渣','每年至少一次','仅未出示记录不能直接证明未检查','不自动判定为重大事故隐患']:self.assertIn(token,h['conditions'])
  self.assertIn('必要时',h['measures']);self.assertIn('严重磨损',h['measures']);self.assertIn('不当作所有销轴或横梁焊缝均须每年单独探伤',k['applicability'])
 def test_reviews_bind_current_entities_and_preserve_full_historical_rejection(self):
  report=json.loads((ROOT/'docs/NEXT_AQ7011_AUTHOR_REVIEW_20261005.json').read_text())
  for f in ['siteFactsConfirmed','rectificationConfirmed','formalApproval','originalPdfsPublished']:self.assertFalse(report[f])
  for group,i in [('laws',LF),('law-versions',LV),('clauses',C),('hazards',H),('links',K)]:
   obj=read(group,i);r=read('reviews/'+group,i);self.assertEqual(r['reviewedContentHash'],content_hash(obj));self.assertEqual(r['decision'],'verified')
   if group in ['hazards','links']:
    old=report['previousRecords'][f'knowledge/{group}/{i}.json']['value'];oldrev=report['previousRecords'][f'knowledge/reviews/{group}/{i}.json']['value']
    self.assertEqual(r['previousDefinition'],old);self.assertEqual(r['previousDefinitionHash'],content_hash(old))
    self.assertEqual(r['previousReview'],oldrev);self.assertEqual(r['historySha256'],content_hash(oldrev))
  r=read('reviews/links',K);self.assertEqual(r['previousReview']['decision'],'rejected');self.assertEqual(r['previousReview']['previousReview']['decision'],'verified')
  self.assertEqual(r['previousDefinition']['clauseId'],'C_MEM10_4_2');self.assertEqual(r['contextHashes'],{'hazard':content_hash(read('hazards',H)),'clause':content_hash(read('clauses',C))})
 def test_gate_admits_general_rule_but_major_topic_does_not(self):
  gate=evaluate_release_gate(ROOT/'knowledge',date(2026,10,5));self.assertIn(H,gate.eligible_hazards);self.assertIn(K,gate.eligible_links)
  topic=public_projection(ROOT/'knowledge',as_of=date(2026,10,5))['topic'];self.assertNotIn(H,topic['hazardIds']);self.assertNotIn(K,{x['linkId'] for x in topic['associations']})
  self.assertFalse(gate.clauses['C_MEM10_4_2']['ok']);self.assertEqual(read('reviews/clauses','C_MEM10_4_2')['decision'],'rejected')
 def test_unverified_ammonia_chains_remain_isolated(self):
  gate=evaluate_release_gate(ROOT/'knowledge',date(2026,10,5))
  for h in ['H_68196C0A0FBDDAF0354E0F71','H_B552B08A4FD28A8770CDC2BB']:
   k='K_XLSX_WEB_'+h;self.assertNotIn(h,gate.eligible_hazards);self.assertNotIn(k,gate.eligible_links)
   self.assertEqual(read('links',k)['clauseId'],'C_MEM10_13');self.assertEqual(read('reviews/links',k)['decision'],'rejected')
if __name__=='__main__':unittest.main()
