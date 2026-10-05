"""Bounded official-source rules: source facts are not enterprise findings."""
import json
from pathlib import Path
import sys
import unittest
from datetime import date
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate

def read(g,i):return json.loads((ROOT/'knowledge'/g/(i+'.json')).read_text())
PENDING=['H_8C14C2BD0D4A4EF1B42FDC8C2E','H_BF7AA7549F8E1B94012882C9','H_C1CE3A649721387F1FC0F7BE','H_1B474A2ABA0E23143E2FE451']
class OfficialClausesTests(unittest.TestCase):
 def test_author_records_preserve_complete_previous_records_and_bind(self):
  for name in ('GENERAL','CYLINDER_GAS'):
   report=json.loads((ROOT/f'docs/OFFICIAL_{name}_INTEGRATION_20261005.json').read_text())
   self.assertFalse(report['siteFactsConfirmed']);self.assertFalse(report['rectificationConfirmed']);self.assertFalse(report['formalApproval']);self.assertFalse(report['originalPdfsPublished'])
   for row in report['decisions']:
    h=read('hazards',row['hazardId']);r=read('reviews/hazards',h['id']);self.assertEqual(r['reviewedContentHash'],content_hash(h))
    self.assertTrue(row['positiveCase']);self.assertTrue(row['negativeCase']);self.assertNotEqual(row['positiveCase'],row['negativeCase'])
    if row['action']=='narrow_existing_stable_id':self.assertEqual(r['previousDefinition']['id'],h['id']);self.assertIn('previousReview',r)
    for kid in row['linkIds']:
     k=read('links',kid);kr=read('reviews/links',kid);c=read('clauses',k['clauseId']);self.assertEqual(kr['reviewedContentHash'],content_hash(k));self.assertEqual(kr['contextHashes'],{'hazard':content_hash(h),'clause':content_hash(c)})
 def test_wood_final_source_and_scope(self):
  k=read('links','K_XLSX_WEB_H_4E5F4BB13B82457DA5377CABDF');self.assertEqual(k['clauseId'],'C_AQ7005_2008_4_6_1');self.assertIn('固定生产场所',k['applicability']);self.assertIn('仅可参照',k['applicability']);self.assertNotEqual(k['clauseId'],'C_GB15577_6_1')
  self.assertIn('或连接集中吸尘设备',read('clauses',k['clauseId'])['quote'])
 def test_unreviewed_new_hose_chain_is_not_in_public_source(self):
  for group,ident in [('hazards','H_GBT14561_HOSE_PLACEMENT'),('laws','LF_STD_GBT14561'),('law-versions','LV_STD_GBT14561_2019'),('clauses','C_GBT14561_2019_5_6_1'),('clauses','C_GBT14561_2019_5_6_2'),('links','K_GBT14561_HOSE_5_6_1'),('links','K_GBT14561_HOSE_5_6_2'),('evidence','E_OFFICIAL_FIRE_HOSE_20261005')]:
   self.assertFalse((ROOT/'knowledge'/group/(ident+'.json')).exists())
 def test_emergency_plug_exception_not_general_ban(self):
  h=read('hazards','H_GB51309_SELF_POWERED_PLUG');q=read('clauses','C_GB51309_2018_4_5_5')['quote']
  for word in ['非集中控制型','自带电源型','采用插头连接','专用工具']:self.assertIn(word,q)
  self.assertIn('不能仅见灯具使用插头即认定违规',h['conditions']);self.assertIn('控制与显示类设备',h['conditions'])
  self.assertEqual(read('evidence','E_OFFICIAL_EMERGENCY_LIGHT_20261005')['sourceClass'],'university-hosted-original')
 def test_sign_temporary_text_is_supporting_not_configuration_duty(self):
  k=read('links','K_GB2894_SIGN_TEMPORARY_7_4_2');self.assertEqual(k['role'],'supporting');self.assertIn('不创造',k['reason']);self.assertEqual(read('clauses',k['clauseId'])['quote'],'在修整或更换安全标志牌时应有临时标志替换。')
 def test_interlock_new_standard_date_and_actual_function_boundary(self):
  h=read('hazards','H_GB12801_ACCIDENT_EXHAUST_INTERLOCK')
  for word in ['企业生产过程','事故排风','2026-10-01','普通舒适性通风','仅缺文件不能证明']:self.assertIn(word,h['conditions'])
  self.assertEqual(read('links','K_GB12801_ACCIDENT_EXHAUST_4_3_6')['clauseId'],'C_12801_4_3_6')
 def test_cylinder_compound_split_recommended_scope(self):
  h=read('hazards','H_200F007CE0EF47DFB8BE2B8618');k=read('links','K_XLSX_NEW14_AB3FE309DCCF562480F0E982')
  self.assertNotIn('10m',h['measures']);self.assertEqual(k['clauseId'],'C_GBT34525_2017_9_1_b')
  for word in ['推荐性','0.2 MPa～35 MPa','0.4 L～3000 L','车用气瓶','军事装备']:self.assertIn(word,k['applicability'])
  self.assertIn('气体的钢印',read('clauses',k['clauseId'])['quote'])
 def test_preuse_check_preserves_referenced_whole_checklist_boundary(self):
  h=read('hazards','H_GBT34525_PREUSE_CHECK');self.assertIn('不把三项当全部检查清单',h['conditions']);self.assertIn('未出示检查记录不直接证明',h['conditions'])
  c=read('clauses','C_GBT34525_2017_8_1_1_c_d_f');self.assertIn('c）、d）、f）',c['articlePath']);self.assertIn('检查内容至少应包括',c['quote'])
 def test_tsg_first_amendment_and_original_terms(self):
  self.assertIn('2024年第42号',read('evidence','E_OFFICIAL_TSG23_AMENDMENT1_20261005')['locator'])
  q=read('clauses','C_TSG23_2021_AM1_1_8_1_3')['quote'];self.assertIn('有特殊要求',q);self.assertIn('非重复充装',q)
  q=read('clauses','C_TSG23_2021_1_7')['quote'];self.assertIn('置换气体除外',q);self.assertIn('混合气体',q);self.assertIn('注1-6',q)
 def test_tsg_amendment_has_real_effective_date_gate(self):
  c='C_TSG23_2021_AM1_1_8_1_3'
  self.assertFalse(evaluate_release_gate(ROOT/'knowledge',date(2024,12,31)).clauses[c]['ok'])
  self.assertTrue(evaluate_release_gate(ROOT/'knowledge',date(2025,1,1)).clauses[c]['ok'])
  self.assertEqual(read('law-versions','LV_META_9215D8555C66CC91A5A5D7A4')['endDate'],'2025-01-01')
 def test_current_tsg_reading_entry_matches_the_effective_amended_version(self):
  v=read('law-versions','LV_TSG23_2021_AM1_2025')
  c=json.loads((ROOT/'source/publication/fulltext/catalog.json').read_text())
  s=json.loads((ROOT/'source/publication/fulltext/search-index.json').read_text())
  rows=[x for x in c['documents'] if x['lawId']==v['lawId']]
  self.assertEqual(len(rows),1);row=rows[0]
  self.assertEqual(row['versionId'],v['id']);self.assertEqual(row['version'],v['versionKey'])
  self.assertEqual(row['effectiveDate'],'2025-01-01');self.assertEqual(row['officialUrl'],v['sourceUrl'])
  self.assertEqual(row['versionAliases'],['LV_META_9215D8555C66CC91A5A5D7A4']);self.assertEqual(row['textMode'],'link_only');self.assertEqual(row['publicationPermission'],'metadata_only');self.assertFalse(row['fullTextReviewed'])
  self.assertIn('2021-06-01',row['validityNote']);self.assertIn('并非合并全文',row['validityNote'])
  sr=[x for x in s['documents'] if x['lawId']==v['lawId']];self.assertEqual(len(sr),1);self.assertEqual(sr[0]['versionId'],v['id']);self.assertEqual(sr[0]['title'],row['title'])
 def test_p01_building_only_not_p02_p05_admission(self):
  h=read('hazards','H_GB55037_BUILDING_GAS_ALARM')
  for word in ['排除住宅建筑','仅建筑内','室外释放源','仅有毒且不燃','民用爆炸物品']:self.assertIn(word,h['conditions'])
  self.assertIn('住宅建筑的燃气用气部位',read('clauses','C_GB55037_2022_8_3_3')['quote'])
 def test_jiangsu_existing_records_are_not_newly_approved(self):
  for i in PENDING:
   self.assertEqual(read('reviews/links','K_XLSX_WEB_'+i)['decision'],'rejected')
  self.assertFalse((ROOT/'knowledge/evidence/E_OFFICIAL_JIANGSU_METAL_20261005.json').exists())
  self.assertFalse((ROOT/'docs/OFFICIAL_JIANGSU_PENDING_20261005.json').exists())
 def test_actual_gate_admits_bounded_rules_and_excludes_pending(self):
  gate=evaluate_release_gate(ROOT/'knowledge',date(2026,10,5))
  ids=[]
  for name in ('GENERAL','CYLINDER_GAS'):
   ids += [x['hazardId'] for x in json.loads((ROOT/f'docs/OFFICIAL_{name}_INTEGRATION_20261005.json').read_text())['decisions'] if x.get('admissionStatus')!='pending_independent_original_page']
  for i in ids:self.assertIn(i,gate.eligible_hazards)
  for i in PENDING+['H_GBT14561_HOSE_PLACEMENT']:self.assertNotIn(i,gate.eligible_hazards)
if __name__=='__main__':unittest.main()
