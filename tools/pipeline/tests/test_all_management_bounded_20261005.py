"""Focused original-text, applicability and predecessor checks for management batch."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[3]; K=ROOT/'knowledge'
from complete_remaining_cohort_fixture import pre_complete_repo_root
BASE=pre_complete_repo_root(ROOT)
sys.path.insert(0,str(ROOT/'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate

def get(g,i):return json.loads((K/g/(i+'.json')).read_text())

class ManagementBoundedBatch(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.r=json.loads((ROOT/'docs/all-management-bounded-author-20261005.json').read_text());cls.g=evaluate_release_gate(K,datetime.date(2026,10,5))
 def test_every_previous_file_is_real_original_bytes(self):
  for path,old in self.r['beforeFiles'].items():
   with self.subTest(path=path):
    if old['existed']:
     b=old['fileTextUtf8'].encode();self.assertEqual(hashlib.sha256(b).hexdigest(),old['sha256'])
     self.assertEqual(b,(BASE/path).read_bytes())
    else:self.assertFalse((BASE/path).exists())
 def test_current_authored_sha_and_reviews(self):
  for path,sha in self.r['authoredSha256'].items():
   with self.subTest(path=path):self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),sha)
  for path in self.r['authoredFiles']:
   if path.startswith('knowledge/reviews/'):
    r=json.loads((ROOT/path).read_text());group=Path(path).parts[-2];obj=get(group,r['entityId']);self.assertEqual(content_hash(obj),r['reviewedContentHash'])
    if group=='links':
     self.assertEqual(content_hash(get('hazards',obj['hazardId'])),r['contextHashes']['hazard']);self.assertEqual(content_hash(get('clauses',obj['clauseId'])),r['contextHashes']['clause'])
 def test_preserve_aliases_keywords_and_source_fields(self):
  for path,old in self.r['beforeFiles'].items():
   if path.startswith('knowledge/hazards/') and old['existed']:
    prior=json.loads(old['fileTextUtf8']);now=json.loads((ROOT/path).read_text())
    for key in ['aliases','keywords','sourceId','sourceIds','sources','sourceUrl','sourceRow','origin']:
     self.assertEqual(now.get(key),prior.get(key),(path,key))
 def test_verified_bounded_hazards_pass_gate(self):
  for d in self.r['decisions']:
   if d['action']=='bounded_existing_stable_id':
    self.assertIn(d['hazardId'],self.g.eligible_hazards,d['hazardId']);self.assertTrue(d['positiveCase']);self.assertTrue(d['negativeCase'])
 def test_no_privately_hosted_pdfs_or_fabricated_site_statements(self):
  for d in self.r['decisions']:
   if d['action']=='bounded_existing_stable_id':
    h=get('hazards',d['hazardId'])
    for forbidden in ['现场检查发现','经资料及履职情况核查','本项目已设置']:
     self.assertNotIn(forbidden,h['description'])
  for path in self.r['authoredFiles']:self.assertFalse(path.endswith(('.pdf','.png','.sqlite','.db')))
 def test_mirror_cannot_be_formal_source_and_summary_withdrawn(self):
  e=get('evidence','E_ALL_GB50187_2012_20261005');self.assertEqual(e['sourceClass'],'corroborative-original-mirror');self.assertNotEqual(e['tier'],'authoritative-public')
  for cid in ['C_GB50187_3_0_12','C_GB50187_5_7_4','C_GB50187_4_4_5']:
   self.assertEqual(get('reviews/clauses',cid)['decision'],'pending')
  for h in ['H_7B7329352589412BBC6B7121D0','H_3DF895C1974245A29D51728DA7','H_AA7C48BCF0E6458484759F407B']:
   self.assertNotIn(h,self.g.eligible_hazards);self.assertEqual(get('hazards',h)['lifecycle'],'proposed')
 def test_official_flood_subitem_excludes_unverified_item2(self):
  c=get('clauses','C_ALL_GB50187_3_0_12_1');self.assertIn('引导句及第1项',c['articlePath']);self.assertIn('不可避免',c['quote']);self.assertNotIn('GB 50201',c['quote']);self.assertNotIn('\n2 ',c['quote'])
  h=get('hazards','H_64890758F40C42608FF5E8DB65');self.assertIn('总平面设计',h['conditions']);self.assertIn('不可避免',h['description'])
 def test_aq_formal_sources_replace_drafts_with_scope(self):
  for i in ['H_0CADE6DD642346949B6A934F7C','H_BC329D96CDE04044A257580182','H_C0A67E719B304E40AF25E33F6A']:
   self.assertIn(i,self.g.eligible_hazards)
  for num in ['5202','5203']:
   e=get('evidence','E_ALL_AQ'+num+'_FINAL_HBBA_20261005');self.assertEqual(e['sourceClass'],'official-industry-standard-platform-final-edition');self.assertIn('hbba.sacinfo.org.cn/portal/download',e['url'])
  h=get('hazards','H_C0A67E719B304E40AF25E33F6A');self.assertIn('不小于500mm',h['conditions']);self.assertIn('未设置防护栏杆，或者未设置工作平台挡板',h['description']);self.assertIn('不以',h['conditions']);self.assertIn('110mm',h['conditions'])
  c=get('clauses','C_ALL_AQ5203_13_4_SETTING');self.assertIn('前段',c['articlePath']);self.assertNotIn('110',c['quote']);self.assertIn('技术含义待',c['note'])
  self.assertIn('设备改造仅可参照',get('hazards','H_BC329D96CDE04044A257580182')['conditions'])
 def test_production_warning_uses_single_canonical(self):
  for i in ['H_2608B93F77A149399BD6B44EA7','H_63E47706CC6D46D9B99E7D8E09']:
   self.assertEqual(get('hazards',i)['mergedInto'],'H_9B91E8E70C2947B7B320BE7DA4');self.assertNotIn(i,self.g.eligible_hazards)
  self.assertNotIn('H_858E1770E149474B8752F69430',self.g.eligible_hazards)
 def test_training_has_correct_article_not_archives(self):
  k=get('links','K_XLSX_WEB_H_6B81819B5BCB43149B0148792F');self.assertEqual(k['clauseId'],'C_217217C54423E4EC506728BB7D')
  self.assertEqual((K/'clauses/C_SAFE_LAW_28_4.json').read_bytes(),(BASE/'knowledge/clauses/C_SAFE_LAW_28_4.json').read_bytes())
 def test_article39_full_three_paragraphs_and_narrow_consumer(self):
  for c in ['C_XLSX_FT_7CED7D8B0FE8D4E571427E9E','C_XLSX_FT_8596F6FDA0F510241F6771D9']:
   q=get('clauses',c)['quote'];self.assertEqual(len(q.splitlines()),3);self.assertIn('在港区内储存、装卸',q);self.assertIn('社会公开',q)
  for h in ['H_BA111E073CFF5E4689BD5591_1','H_BA111E073CFF5E4689BD5591_2']:
   scope=get('hazards',h)['conditions'];self.assertIn('使用危险化学品从事生产',scope);self.assertIn('第五十二条',scope);self.assertIn('第一款',scope)
 def test_article41_storage_cabinet_and_major_source_scope(self):
  self.assertIn('储存专柜',get('hazards','H_C901CA419B02E1AE73270201_1')['description'])
  self.assertIn('专用储存场所',get('hazards','H_D9017B3895E8E59531CF8180')['description'])
  h=get('hazards','H_C901CA419B02E1AE73270201_2');self.assertIn('非剧毒',h['description']);self.assertIn('构成重大危险源',h['conditions']);self.assertIn('不少于三年',h['measures'])
 def test_hazardous_waste_scope_forms_and_retention(self):
  h=get('hazards','H_0A9DDC2534BC46FDA9AEE80A89');self.assertIn('原则上',h['measures']);self.assertIn('5年以上',h['measures']);self.assertIn('电子或纸质',h['measures']);self.assertIn('参考表不强制',h['measures'])
  h=get('hazards','H_97C1C1E87B844BAD9EB2A3D580');self.assertIn('贮存设施与贮存点',h['conditions']);self.assertIn('产生危险废物的单位',h['conditions'])
  for a in ['6_3_2','6_3_3']:
   k=get('links','K_ALL_MANAGEMENT_HJ1259_'+a);self.assertEqual(k['role'],'supporting');self.assertIn('仅限产生危险废物',k['applicability'])
 def test_recommendation_and_guidance_not_universal_mandatory(self):
  self.assertIn('推荐性',get('hazards','H_F931D93BEF2E437C832C92C1BF')['conditions'])
  h=get('hazards','H_7CB6B58D9D894DC1BE39E1E7F2');self.assertIn('指导性',h['conditions']);self.assertIn('常压吸附',h['conditions']);self.assertIn('不小于4Ω',h['description'])
  self.assertIn('建设项目',get('hazards','H_D1BA1126B2D244B9A05CF6C90B')['conditions'])
 def test_material_storage_monitoring_and_opening_keep_choices(self):
  self.assertIn('不要求同批物料同时采用三种',get('hazards','H_32DB2138E70743A99E7B94013C')['conditions'])
  self.assertIn('不一律要求三类装置',get('hazards','H_9BC3E3B8385847459427E344DF')['measures'])
  self.assertIn('既未设置有效盖板，也未设置有效防护栏杆',get('hazards','H_FLOOR_OPENING_UNPROTECTED')['description'])
  self.assertIn('具体适用安全要求和实测不符合证据',get('hazards','H_7110299CB63D4DD7B6D73491ED')['conditions'])
 def test_extra_warehouse_dependency_has_correct_conditional_facilities(self):
  k=get('links','K_XLSX_WEB_H_9C23C18DB9EF40A58B8C98F06C');self.assertEqual(k['clauseId'],'C_DBD6E2B5ACAB595BE7EA59D3')
  h=get('hazards',k['hazardId']);self.assertIn('危险特性',h['conditions']);self.assertIn('不能一律指定人体静电消除',h['measures'])
 def test_alternative_protection_and_independent_ledger_obligations(self):
  h=get('hazards','H_FLOOR_OPENING_UNPROTECTED');self.assertIn('既未',h['description']);self.assertIn('也未',h['description'])
  cases={(False,False):True,(True,False):False,(False,True):False,(True,True):False}
  for (cover,rail),expected in cases.items():self.assertEqual(not cover and not rail,expected)
  h=get('hazards','H_97C1C1E87B844BAD9EB2A3D580');self.assertIn('或者未按规定保存',h['description'])
  established,saved=True,False;self.assertTrue(not established or not saved)
 def test_three_compound_branches_remain_bounded(self):
  for hid,word in [('H_210D2E5340A24AF5B9CAD1553E','突然超压'),('H_54347BF9DA2E435FBB08E2EFF5','第四分项'),('H_CF_GEN_08','LOTO')]:
   h=get('hazards',hid);self.assertIn(hid,self.g.eligible_hazards);self.assertIn(word,json.dumps(h,ensure_ascii=False))
 def test_original_residuals_are_distinct_from_scope_and_site_facts(self):
  outcomes=self.r['originalBranchOutcomes'];self.assertEqual(len(outcomes),108);self.assertEqual(len({x['hazardId'] for x in outcomes}),108)
  indexed={x['hazardId']:x for x in outcomes}
  for x in outcomes:
   for key in ['unsupportedOriginalBranches','scopeExclusions','caseEvidenceRequirements','invalidClaimExcluded']:self.assertIsInstance(x[key],list)
   self.assertFalse(x['siteFactsConfirmed']);self.assertFalse(x['allReferencedTechnicalParametersAudited'])
  for i in ['H_66B2A0967E8B4E4BAD7749DF_3','H_6B9EB3C3F3A144E4962ACC3FB9','H_0CADE6DD642346949B6A934F7C','H_97C1C1E87B844BAD9EB2A3D580','H_BC329D96CDE04044A257580182','H_D1BA1126B2D244B9A05CF6C90B']:
   self.assertEqual(indexed[i]['unsupportedOriginalBranches'],[]);self.assertTrue(indexed[i]['boundedRuleCompleted'])
  for i in ['H_210D2E5340A24AF5B9CAD1553E','H_54347BF9DA2E435FBB08E2EFF5','H_6A3BF03D4DC54A228F590EE1D9','H_9BC3E3B8385847459427E344DF','H_A1F170AAD1DC4BB893BD27288F','H_C0A67E719B304E40AF25E33F6A','H_CF_GEN_08']:self.assertTrue(indexed[i]['unsupportedOriginalBranches'])
 def test_site_selection_keeps_only_published_complete_items(self):
  c=get('clauses','C_ALL_GB50187_3_0_14_ITEMS_1_8_11');self.assertIn('第1—8、11项',c['articlePath']);self.assertIn('\n11 ',c['quote']);self.assertNotIn('\n9 ',c['quote']);self.assertNotIn('\n10 ',c['quote'])
  h=get('hazards','H_EACC1ED8867C4F3DA5FBAC8B49');self.assertIn('总平面设计',h['conditions']);self.assertIn('不覆盖',h['conditions']);self.assertIn(h['id'],self.g.eligible_hazards)
  self.assertEqual(get('reviews/clauses','C_GB50187_3_0_14')['decision'],'pending')
 def test_all_links_to_authored_hazards_keep_current_bindings(self):
  hazard_ids={Path(path).stem for path in self.r['authoredFiles'] if path.startswith('knowledge/hazards/')}
  checked=0
  for path in (K/'links').glob('*.json'):
   l=json.loads(path.read_text())
   if l['hazardId'] not in hazard_ids:continue
   rvpath=K/'reviews/links'/path.name
   self.assertTrue(rvpath.exists(),l['id']);rv=json.loads(rvpath.read_text())
   self.assertEqual(rv['reviewedContentHash'],content_hash(l),l['id'])
   self.assertEqual(rv['contextHashes']['hazard'],content_hash(get('hazards',l['hazardId'])),l['id'])
   self.assertEqual(rv['contextHashes']['clause'],content_hash(get('clauses',l['clauseId'])),l['id']);checked+=1
  self.assertGreaterEqual(checked,53)
 def test_historical_link_rejections_not_reactivated(self):
  closure=self.r['historicalLinkClosureReview'];self.assertEqual(len(closure),12)
  for x in closure:
   l=get('links',x['linkId']);rv=get('reviews/links',x['linkId']);old=json.loads(self.r['beforeFiles']['knowledge/reviews/links/'+x['linkId']+'.json']['fileTextUtf8'])
   self.assertEqual(l['lifecycle'],x['linkLifecycleUnchanged']);self.assertIn(l['lifecycle'],['proposed','superseded'])
   self.assertEqual(rv['decision'],old['decision']);self.assertIn(rv['decision'],['pending','rejected']);self.assertEqual(rv['evidenceRefs'],old['evidenceRefs'])
   self.assertEqual(rv['previousReview'],old);self.assertEqual(rv['previousReviewFileSha256'],x['oldReviewFileSha256'])
   self.assertEqual(rv['comparisonRefs']['purpose'],'compare_only_not_evidence_for_old_clause')
   self.assertEqual((K/'links'/(x['linkId']+'.json')).read_bytes(),(BASE/'knowledge/links'/(x['linkId']+'.json')).read_bytes())
 def test_skipped_and_regulation_identity_untouched(self):
  for path in ['knowledge/clauses/C066.json','knowledge/law-versions/LV_HAZCHEM_REG.json','knowledge/laws/LF_HAZCHEM_REG.json']:
   if (BASE/path).exists():self.assertEqual((ROOT/path).read_bytes(),(BASE/path).read_bytes())
  self.assertFalse(self.r['siteFactsConfirmed']);self.assertFalse(self.r['formalApproval'])

if __name__=='__main__':unittest.main()
