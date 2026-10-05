"""Exact source, scope, history and negative admission tests for bounded electrical repair."""
import copy
from datetime import date
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[3]
KNOW=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate,gate_hazard_content,gate_link,gate_clause

def read(kind,ident):return json.loads((KNOW/kind/(ident+'.json')).read_text())
LIGHT='H_CFF821DDE6764083BFB914EC86'
CHEM='H_3141FAD634694686B722139F91'
OLD='H_1251ED2287FB47B6BDED9292D1'
CABLE='H_C7284453E8E94532A44FC5F5EF'
FLANGE='H_12158_10_1_2'
MON='H_974023DBBC2B471AA3F7DB6A67'
DIRECT={LIGHT:'K_XLSX_WEB_'+LIGHT,CHEM:'K_XLSX_WEB_'+CHEM,CABLE:'K_NEXT_GB50054_REAGENT_CABLE_7_6_38',MON:'K_NEXT_GBT13869_MONITOR_5_2_1'}
REJECTED=['K_XLSX_NEW14_A6A5CAC97BDE0A07FB0D52B3','K_XLSX_NEW14_A4C0585CBE2BEAF3CADD58FE','K_XLSX_WEB_H_12158_10_1_2']

class BoundedElectrical20261005(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.gate=evaluate_release_gate(KNOW,date(2026,10,5))

 def test_four_bounded_definitions_have_exact_direct_links(self):
  for hid,kid in DIRECT.items():
   with self.subTest(hazard=hid):
    self.assertIn(hid,self.gate.eligible_hazards)
    self.assertEqual(self.gate.qualifying_links_by_hazard[hid],[kid])
    self.assertEqual(read('links',kid)['role'],'direct')

 def test_complete_lightning_clause_and_all_consumers(self):
  c=read('clauses','C_GB50057_4_1_1')
  self.assertEqual(c['quote'],'各类防雷建筑物应设防直击雷的外部防雷装置，并应采取防闪电电涌侵入的措施。\n第一类防雷建筑物和本规范第3.0.3条第5～7款所规定的第二类防雷建筑物，尚应采取防闪电感应的措施。')
  consumers=[json.loads(p.read_text()) for p in (KNOW/'links').glob('*.json')]
  consumers=[k for k in consumers if k['clauseId']==c['id']]
  self.assertEqual({k['hazardId'] for k in consumers},{LIGHT,CHEM})
  for k in consumers:
   h=read('hazards',k['hazardId']);rv=read('reviews/links',k['id'])
   self.assertEqual(rv['contextHashes'],{'hazard':content_hash(h),'clause':content_hash(c)})
   for token in ('新建、扩建、改建','仅消费4.1.1第一段','不是所有建筑无条件适用','GB55024-2022','未出示检测报告'):
    self.assertIn(token,h['conditions'])
  self.assertNotIn('该公司',read('hazards',LIGHT)['measures'])
  self.assertIn('原描述中的定期检测义务未由本C证明',read('hazards',CHEM)['conditions'])

 def test_synonym_merge_retains_ids_without_admitting_inspection_branch(self):
  h=read('hazards',OLD);rv=read('reviews/hazards',OLD)
  self.assertEqual(h['lifecycle'],'superseded');self.assertEqual(h['mergedInto'],LIGHT)
  self.assertNotIn(OLD,self.gate.eligible_hazards)
  self.assertIn('定期检测不包含',rv['mergeBoundary'])
  self.assertEqual(rv['previousDefinition']['id'],OLD)
  self.assertIn('定期检测',rv['previousDefinition']['measures'])

 def test_cable_underground_section_and_selected_crossing_boundary(self):
  h=read('hazards',CABLE);c=read('clauses','C_NEXT_GB50054_7_6_38_20261005')
  for token in ('电缆埋地敷设','交流、工频1000V','穿过建筑物的墙体或楼板','不覆盖试剂室全部线路','不以房间名称推定爆炸危险区或必须钢管','不在原公告强制性条文清单'):
   self.assertIn(token,h['conditions'])
  self.assertIn('1.5倍',h['measures'])
  self.assertEqual(c['quote'],'电缆通过下列地段应穿管保护，穿管内径不应小于电缆外径的1.5倍：\n1 电缆通过建筑物和构筑物的基础、散水坡、楼板和穿过墙体等处；\n2 电缆通过铁路、道路处和可能受到机械损伤的地段；\n3 电缆引出地面2m至地下200mm处的部分；\n4 电缆可能受到机械损伤的地方。')
  self.assertIn('试剂室内电缆未按规范',read('reviews/hazards',CABLE)['previousDefinition']['description'])

 def test_glove_contamination_cleanup_does_not_merge_distinct_duties(self):
  h=read('hazards',FLANGE);rv=read('reviews/hazards',FLANGE)
  self.assertEqual(h['lifecycle'],'proposed');self.assertEqual(h['mode'],'candidate')
  self.assertIsNone(h['mergedInto']);self.assertEqual(rv['decision'],'pending')
  self.assertNotIn(FLANGE,self.gate.eligible_hazards)
  self.assertIn('旧注释不成立',h['note'])
  self.assertIn('合并至 H_12158_10_2_1',rv['previousDefinition']['note'])
  self.assertIn('不将污染清理计作技术定义完整闭环',rv['reason'])

 def test_monitoring_is_distinct_from_overload_and_not_automatic_only(self):
  h=read('hazards',MON);k=read('links',DIRECT[MON]);c=read('clauses',k['clauseId'])
  self.assertEqual(c['lawVersionId'],'LV_STD_GBT13869_2017')
  self.assertIn('应有必要的监控或监视措施；用电产品不允许超负荷运行',c['quote'])
  for token in ('交流1000V及以下、直流1500V及以下','不推定必须自动化或连续人工盯守','未见监控不等于已经超负荷','2027-02-01','推荐性国家标准'):
   self.assertIn(token,h['conditions'])
  self.assertNotIn('超负荷',h['title']);self.assertNotIn('超负荷',h['description'])
  self.assertIn('存在超负荷运行',read('reviews/hazards',MON)['previousDefinition']['description'])

 def test_wrong_direct_links_stay_rejected_and_historically_traceable(self):
  for kid in REJECTED:
   k=read('links',kid);rv=read('reviews/links',kid)
   self.assertEqual(k['lifecycle'],'superseded');self.assertEqual(rv['decision'],'rejected')
   self.assertNotIn(kid,self.gate.eligible_links)
   self.assertEqual(rv['reviewedContentHash'],content_hash(k))
   self.assertTrue(rv['previousReview']);self.assertEqual(rv['previousDefinition']['id'],kid)

 def test_scope_and_quote_mutations_do_not_inherit_approval(self):
  for hid,kid in DIRECT.items():
   h=read('hazards',hid);hr=read('reviews/hazards',hid)
   self.assertTrue(gate_hazard_content(h,hr)[0])
   bad=copy.deepcopy(h);bad['conditions']='所有场所全部适用。'
   self.assertFalse(gate_hazard_content(bad,hr)[0])
   k=read('links',kid);c=read('clauses',k['clauseId']);lv=read('law-versions',c['lawVersionId']);law=read('laws',lv['lawId']);kr=read('reviews/links',kid)
   self.assertTrue(gate_link(k,kr,h,c,law,True)[0])
   self.assertFalse(gate_link(k,kr,bad,c,law,True)[0])
  c=read('clauses','C_NEXT_GB50054_7_6_38_20261005');rv=read('reviews/clauses',c['id']);lv=read('law-versions',c['lawVersionId'])
  bad=copy.deepcopy(c);bad['quote']=bad['quote'].replace('1.5倍','2倍')
  self.assertTrue(gate_clause(c,rv,True,True,lv)[0]);self.assertFalse(gate_clause(bad,rv,True,True,lv)[0])

 def test_source_identity_and_force_are_not_inferred_from_pdf_presence(self):
  e=read('evidence','E_NEXT_GB50057_EXACT_20261005');self.assertIn('824号',e['locator']);self.assertIn('误写606号',e['notes'])
  e=read('evidence','E_NEXT_GB50054_EXACT_20261005');self.assertIn('1100号',e['locator']);self.assertIn('不含6.1.1或7.6.38',e['notes'])
  e=read('evidence','E_NEXT_GB55024_RELATION_20261005');self.assertEqual(e['url'],'https://szwb.sz.gov.cn/gwszwfw/zsk/hybz/content/post_9913357.html')
  self.assertIn('不能混同GB50057',e['notes']);self.assertIn('不以未列入推断所有后续文件均未调整',e['notes'])
  e=read('evidence','E_NEXT_GBT13869_STATUS_20261005');self.assertIn('2027-02-01',e['notes'])
  self.assertEqual(read('law-versions','LV_STD_GBT13869_2026')['validityStatus'],'upcoming')

 def test_partial_composites_and_skips_are_not_reported_as_complete(self):
  report=json.loads((ROOT/'docs/NEXT_BOUNDED_ELECTRICAL_REPAIR_20261005.json').read_text())
  remaining={x['hazardId']:x for x in report['remainingBranches']}
  for hid in ['H_0AF2C63369124DA5BCDEFBF340','H_9C4FE3EBE8C149EFB882B60148']:
   self.assertTrue(remaining[hid]['unresolvedBranch']);self.assertEqual(read('hazards',hid)['lifecycle'],'proposed')
   self.assertNotIn(hid,self.gate.eligible_hazards)
  self.assertEqual(remaining['H_6F7D6D7E28DD423B9F40AF8218']['action'],'skip_source_gap')
  self.assertEqual(remaining['H_409ABC97960D46FBBF6AA54D28']['action'],'skip_scope_gap')
  self.assertFalse(report['originalPdfsPublished']);self.assertFalse(report['siteFactsConfirmed'])

 def test_protected_prior_work_is_unchanged(self):
  expected={'hazards/H_4E5F4BB13B82457DA5377CABDF': '0f85ea33c1451d86914a171e35971d5e6363ba968c87484544b3ad0a6c09c5f4', 'links/K_XLSX_WEB_H_4E5F4BB13B82457DA5377CABDF': '90a75244b3af8b78768214c5c5175a8beacc31866268dfa3a1034eaaa162c5c6', 'hazards/H_GB51309_SELF_POWERED_PLUG': 'fa7063c658c77924693e4b16a0955da2caedde11bcfd94a5ac70bd67772e9921', 'links/K_GB51309_SELF_POWERED_PLUG_4_5_5': '7f1eda4c6c1ac20e68b0d5fb04f4868b19d5906b109a2f74b0e2ef03a7c18406', 'hazards/H_GB12801_ACCIDENT_EXHAUST_INTERLOCK': '85de0153527f324fdf74d3e43b6ab450858c59cbe20925a51230a19120005a74', 'links/K_GB12801_ACCIDENT_EXHAUST_4_3_6': 'c3f905661fad8f241088d84b2b7f4ad4093db02ecb62305b8a8b79f00e1e340e', 'hazards/H_GB3836_UNUSED_ENTRY': '7440b8063f43dfa9fca22177624306c7df792d64153b76acc920f3fdc8f3ae65', 'links/K_GB3836_UNUSED_ENTRY_6_4_4': '7f8c0861f97224e2e4dfa5f82505edc06c7fffc8ad851312d52489b133edd6ff', 'hazards/H_GB3836_EX_D_MISSING_FASTENER': '0e22e7584107ce365f4d7b5be7f818282460c1360f6709f0403c7efd7968870f', 'links/K_GB3836_EX_D_INITIAL_B_1_A11': 'da2392bb8bcb6fd370e4d6d496503ec7ec3d86e3c43c3b1f7df592b2b10158e5', 'links/K_GB3836_EX_D_INITIAL_8': 'f6627d65268a4f37c1164225bc4e8b6bd3bb8bb99971440bdab81f31bca388d7', 'links/K_GB3836_EX_D_MAINT_A_1_A11': '18a815f32e8f6d465b78ff3c0f73f6a011a1d39b45d54c90478e4bc3bd8314d8', 'links/K_GB3836_EX_D_MAINT_5_7_1': '6671c9dd7e16d279e191f86052b592f711f6904d2c069b958258d6c3fb6d45bb', 'links/K_GB3836_EX_D_MAINT_6_1': '19bb6e18a559469ce52c79babb39bc309850395b986e1354e4c913bf0f6c385a', 'hazards/H_200F007CE0EF47DFB8BE2B8618': '1f05e16429d1b5be45aaf114537f26694c47b81a843e15940214431087391e90', 'links/K_XLSX_NEW14_AB3FE309DCCF562480F0E982': 'fd61f5b1dd1ab119fb2319a0a73e1235116aa4fb4e6eeddfd56897fae2327fd4', 'hazards/H_GBT34525_PREUSE_CHECK': '748ace04f24959446baddc8ff373663b950bc0d25622e59142dfb943e9c8b6f6', 'links/K_GBT34525_PREUSE_9_1_a': 'effb0382cf9a8d9d8a9996134b47117735563af3a5626a7eddb27b4103f410a6', 'links/K_GBT34525_PREUSE_8_1_1_c_d_f': '5500142b213c99d280784f2d0983af5ba637a6f1729488daf381fc0705847108', 'hazards/H_GB55037_BUILDING_GAS_ALARM': 'e42d3562c5e2fdcc416e72ff7519b85d2073bfe7d19f341440f055b5fbc36983', 'links/K_GB55037_BUILDING_GAS_ALARM_8_3_3': 'a3adcbe31da6b4835eaa6ab4e04e93dab82b90aff6e05032bef15c952ea811af', 'links/K_GB55037_BUILDING_GAS_ALARM_SCOPE': 'e8eca8e1bb87027615c3023516e94360b7dd848beacca30f5eb707a4a38acdd6', 'hazards/H_12158_9_11_1': '30d4e4e3f3562a25dcb43215ad1e25f3cb1b0cc2ed6f6f71897b2a1f3415997a', 'links/K_XLSX_c231a40034d6dce8a2b9c8a9': 'ba1e7f9618123baaab7f8c2d562c29d3480677f56407e1f5f064c601d8c26ae6', 'hazards/H_12158_9_11_2': 'b3bfd7194cb595a410a365ff484ad2db39c1a2b756325c9ec4e761c46703e298', 'links/K_XLSX_8d7b114927822b1c33d28104': '8465be809762fec3edcb36b0b6983fff250a5d89676b0159f3a571306fdb0733', 'hazards/H_12158_9_11_3': '3c59d63d1e722cbd892e654061d7d01c8b09aade8edeebb8549f6174af7613f7', 'links/K_XLSX_11d25033369ed548886a4b28': '350077a09ceeff36c43419248ae9fa41756668e127cd7f34042f3f2ec96c623e', 'hazards/H_1A8786209C974B6BB28C4ADFA5': '92f221d41821ab2ea4e41ec8e8a41a07265d7ef8550c02633bb0f2b7933f14bc', 'links/K_1A878620_GBT13869_5_2_1': 'e8e6c3665bdfbada47c3f13f13fef42c2938f7620edfa8defef44d707ce9235d', 'hazards/H029': '8284a4f3eea6fee0e5d0be06d8c599def774915fa17a911dc3045e0581824e4b', 'links/K_XLSX_SPECIAL_BFA056A1605176B84B7502DD': '573ebca528a8bfbc7a73fc35f22988f9bfdbc2eaeac7f828205c762b1e883fc9', 'hazards/H_0AF2C63369124DA5BCDEFBF340': 'e5f87e9b31159b0fe491de147dce44762141fd409ae115478c4c9f5b0c800a8e', 'hazards/H_9C4FE3EBE8C149EFB882B60148': '3e72357e7751505a74ce8a42817d8c6bd21bb7adda68bddd1b6c07ba79c2fa9c', 'hazards/H_62AD7AADA05F468BAE0F91F5CC': '18058a928ed84ee231e0b131c434cf1ce73f1f24df16d7e245ac4f8c809291ac', 'links/K_XLSX_NEW14_E4704777D743EC11C3C851C3': '748795c113aebcecc8bd30c481884c9e74f7648fda2cf316d9afca3cb6f562aa'}
  for key,digest in expected.items():
   kind,ident=key.split('/')
   with self.subTest(key=key):self.assertEqual(content_hash(read(kind,ident)),digest)

if __name__=='__main__':unittest.main()
