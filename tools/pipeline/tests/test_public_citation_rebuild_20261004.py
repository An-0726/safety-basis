"""Bounded author reconstruction checks; no approval or historical-cohort bypass."""
import hashlib
import json
from datetime import date
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[3]
from recovery_cohort_fixture import pre_recovery_repo_root
_AUTHOR_COHORT = json.loads((Path(__file__).parent/'fixtures/public_citation_rebuild_20261004.json').read_text())
_CURRENT_ROOT = ROOT
_MERGE = json.loads((ROOT/'docs/EXTINGUISHER_DUPLICATE_MERGE_20261004.json').read_text())
ROOT = pre_recovery_repo_root(ROOT, keep_paths=set(_AUTHOR_COHORT['records']) | {'docs/PUBLIC_CITATION_REBUILD_20261004.json'})
# This test asserts the original, independently reviewed 80-file author cohort.
# The later exact duplicate merge has its own current-source/negative tests.
# Only its eight pinned paths may be reversed in this temporary historical view.
for _path, _change in _MERGE['records'].items():
 if hashlib.sha256((_CURRENT_ROOT/_path).read_bytes()).hexdigest() != _change['afterSha256']:
  raise AssertionError('Unrecognized post-author merge mutation: '+_path)
 if _path not in _AUTHOR_COHORT['records'] or _AUTHOR_COHORT['records'][_path]['afterFileText'] != _change['beforeFileText']:
  raise AssertionError('Merge predecessor differs from reviewed author cohort: '+_path)
 if hashlib.sha256(_change['beforeFileText'].encode()).hexdigest() != _change['beforeSha256']:
  raise AssertionError('Corrupt post-author predecessor: '+_path)
 (ROOT/_path).write_text(_change['beforeFileText'])
KNOW=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate
from major_criteria import public_projection
F=json.loads((Path(__file__).parent/'fixtures/public_citation_rebuild_20261004.json').read_text())
def read(kind,ident): return json.loads((KNOW/kind/(ident+'.json')).read_text())
def sha(raw):return hashlib.sha256(raw).hexdigest()
PAINT='H_366610E8AA084C77844EFFBAAD'
FIRE=['H027','H_AA8D8CAF77964A0DBC39CDB146','H_GB50140_5_1_3_1','H_08C1576EE4824ED8BE0CDD56DF','H_16A5C551A3BE44329C7B5101CB','H_AD8892D4501D426680ED439882','H_365F2FD05EA345A8A4E71BC9B9','H_9FDD968713424B6CB3EC721C3D']
class PublicCitationRebuildTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.gate=evaluate_release_gate(KNOW,date(2026,10,4))
 def test_exact_candidates_and_old_bytes(self):
  self.assertEqual(len(F['records']),80)
  for p,row in F['records'].items():
   raw=(ROOT/p).read_bytes();self.assertEqual(sha(raw),row['afterSha256'],p);self.assertEqual(raw.decode(),row['afterFileText'],p)
   if row['beforeFileText'] is not None:self.assertEqual(sha(row['beforeFileText'].encode()),row['beforeSha256'],p)
 def test_all_reviews_preserve_history_and_bind_actual_entities(self):
  for p,row in F['records'].items():
   if '/reviews/' not in p:continue
   r=json.loads(row['afterFileText']);old=json.loads(row['beforeFileText']) if row['beforeFileText'] else None
   self.assertEqual(r['checkedAt'],'2026-10-04');self.assertFalse(r['reviewEvidence']['independentApproval'])
   if old is not None:
    self.assertEqual(r['previousReview'],old,p);self.assertEqual(r['previousReviewFileSha256'],row['beforeSha256']);self.assertEqual(r['historySha256'],content_hash(old))
   kind=p.split('/')[2];d=read(kind,r['entityId']);self.assertEqual(r['reviewedContentHash'],content_hash(d))
   self.assertEqual(r['reviewedValues'],{x:d[x[1:]] for x in r['reviewedFields']})
   self.assertIsInstance(r['evidenceRefs'],list)
   for e in r['evidenceRefs']:self.assertIsInstance(e,str);self.assertTrue((KNOW/'evidence'/(e+'.json')).exists(),e)
   if kind=='links':
    self.assertEqual(r['contextHashes']['hazard'],content_hash(read('hazards',d['hazardId'])));self.assertEqual(r['contextHashes']['clause'],content_hash(read('clauses',d['clauseId'])))
 def test_protected_sources_are_unchanged(self):
  for p,expected in F['protectedFiles'].items():self.assertEqual(sha((ROOT/p).read_bytes()),expected,p)
  self.assertEqual(read('reviews/clauses','C_XLSX_FT_90224871C689F7B4C8AF1995')['decision'],'rejected')
  self.assertEqual(read('reviews/clauses','C_MEM10_13')['decision'],'rejected')
 def test_paint_has_correct_independent_or_branch_and_mechanical_scope(self):
  h=read('hazards',PAINT);k=read('links','K_XLSX_WEB_'+PAINT)
  self.assertEqual(k['clauseId'],'C_PDDB_7');self.assertIn('只消费第（七）项',k['reason'])
  self.assertIn('或者',h['description']);self.assertNotIn('也未',h['description']);self.assertIn('不要求两项同时缺失',h['conditions'])
  for token in ['仅适用于机械企业','非水性漆','任一未设置','不能在整改时二选一','仅使用水性漆','非机械企业']:self.assertIn(token,h['conditions'])
  self.assertNotIn('喷漆室已安装',h['measures']);self.assertIn('两类设施均',h['measures']);self.assertIn(PAINT,self.gate.eligible_hazards)
 def test_exact_major_association_added_without_promoting_other_pending_links(self):
  p=public_projection(KNOW,as_of=date(2026,10,4));self.assertEqual(p['inventory']['excluded'],[])
  self.assertEqual(len(p['topic']['hazardIds']),21);self.assertEqual(len(p['catalog']['standards']),6)
  rows=[x for x in p['topic']['associations'] if x['hazardId']==PAINT];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['clauseId'],'C_PDDB_7')
  config=read('major-criteria/v1','catalog');s=next(x for x in config['standards'] if x['lawVersionId']=='L019')
  self.assertNotIn('K_XLSX_WEB_'+PAINT,[x['linkId'] for x in s['pendingTopicLinks']]);self.assertEqual(len(s['pendingTopicLinks']),3)
 def test_false_gb50444_locators_restore_their_own_actual_text(self):
  self.assertEqual(read('clauses','C_GB50444_5_1_3')['quote'],'检查或维修后的灭火器均应按原设置点位置摆放。')
  q=read('clauses','C_GB50444_5_2_3')['quote'];self.assertIn('日常巡检',q);self.assertIn('应及时处置',q);self.assertNotIn('记录',q)
  self.assertEqual(read('clauses','C_GB50444_5_2_4')['quote'],'灭火器的检查记录应予保留。')
  self.assertFalse(any(x['clauseId'] in {'C_GB50444_5_1_3','C_GB50444_5_2_3','C_XLSX_GB50444_3_1_5'} and x['ok'] for x in self.gate.links.values()))
 def test_height_and_stability_preserve_modality_and_design_scope(self):
  for h in ['H_AA8D8CAF77964A0DBC39CDB146','H_GB50140_5_1_3_1','H_08C1576EE4824ED8BE0CDD56DF']:
   self.assertEqual(read('links','K_XLSX_WEB_'+h)['clauseId'],'C_GB50140_5_1_3');self.assertIn('新建、改建、扩建',read('hazards',h)['conditions'])
  q=read('clauses','C_GB50140_5_1_3')['quote'];self.assertIn('底部离地面高度不宜小于0.08m',q);self.assertIn('顶部离地面高度不应大于1.50m',q)
  h=read('hazards','H_GB50140_5_1_3_1');self.assertNotIn('且',h['title']);self.assertIn('不因未装箱而自动命中',h['conditions'])
  h=read('hazards','H_AA8D8CAF77964A0DBC39CDB146');self.assertIn('不得仅凭落地',h['conditions']);self.assertIn('第3.2.7条',h['conditions'])
 def test_insurance_device_uses_exact_table_row_and_parent_obligation(self):
  k=read('links','K_XLSX_WEB_H_16A5C551A3BE44329C7B5101CB');self.assertEqual(k['clauseId'],'C_GB50444_APP_C_14')
  q=read('clauses',k['clauseId'])['quote'];self.assertIn('每月进行一次检查',q);self.assertIn('14. 灭火器的铅封、销闩等保险装置是否未损坏或遗失',q)
  self.assertNotIn('不得上锁',q);self.assertIn('不复活已废止2.2.1',read('hazards',k['hazardId'])['note'])
 def test_monthly_halfmonth_and_record_retention_have_separate_direct_links(self):
  for h in ['H_AD8892D4501D426680ED439882','H_365F2FD05EA345A8A4E71BC9B9']:
   links=[x for x in self.gate.links.values() if x['hazardId']==h and x['ok']]
   self.assertEqual({x['clauseId'] for x in links},{'C_GB50444_5_2_1','C_GB50444_5_2_2','C_GB50444_5_2_4'})
   d=read('hazards',h);self.assertIn('不要求同时存在',d['conditions']);self.assertIn('纸质或电子记录',d['conditions']);self.assertIn('每半月',d['conditions'])
  c=read('clauses','C_GB50444_5_2_2')['quote'];self.assertEqual(len(c.splitlines()),3);self.assertIn('地下室',c)
 def test_replacement_and_environment_use_current_norm_not_revoked_commentary(self):
  h=read('hazards','H_9FDD968713424B6CB3EC721C3D');self.assertIn('或者',h['description']);self.assertIn('等效替代',h['measures']);self.assertNotIn('且',h['title'])
  k=read('links','K_XLSX_GB50444_32DF1CAD7352873891996CEF');self.assertEqual(k['clauseId'],'C_GB55036_10_0_5');self.assertEqual(read('reviews/clauses','C_XLSX_GB50444_3_1_5')['decision'],'rejected')
  h=read('hazards','H027');self.assertIn('可能超出',h['description']);self.assertIn('或者',h['description']);self.assertIn('两义务分别',k['reason'])
 def test_truncated_legal_articles_are_complete_without_scope_inflation(self):
  c=read('clauses','C_XLSX_FT_1728309ECD70DC916104FFD7');self.assertEqual(len(c['quote'].splitlines()),6)
  for token in ['（一）','（二）','（三）','（四）','（五）']:self.assertIn(token,c['quote'])
  h=read('hazards','H_CD607239BF80F8B8DE00715233_1');self.assertIn('只核未建立',h['conditions']);self.assertIn('不直接等同于完全未建立',h['conditions'])
  c=read('clauses','C_XLSX_FT_6414147BBCB0412CB030D3A1');self.assertEqual(len(c['quote'].splitlines()),4);self.assertEqual(c['jurisdictionCode'],'CN-32')
  h=read('hazards','H_A555A3CADE35BAE4AE5D7435EB_1');self.assertIn('每天工作前',h['conditions']);self.assertIn('不得仅凭没有纸质检查表',h['conditions']);self.assertIn('不扩展为全国',h['conditions'])
 def test_current_membership_changes_are_exact_and_no_old_hazard_is_removed(self):
  d=F['gateSnapshots']['2026-10-04'];self.assertEqual(d['hazardsAdded'],[PAINT]);self.assertEqual(d['hazardsRemoved'],[])
  self.assertEqual(len(self.gate.eligible_hazards),d['afterCounts']['hazards']);self.assertEqual(len(self.gate.eligible_links),d['afterCounts']['links'])
  self.assertTrue(set(FIRE)<=self.gate.eligible_hazards)
 def test_sources_are_actual_originals_and_candidate_cases_cover_exclusions(self):
  expected={'E_PUBLIC_GB50444_ORIGINAL_20261004':'b1d1810e872f78ce3ca4333626f6e95ff5f8efed42bce7da39208c72e51662b9','E_PUBLIC_GB50140_ORIGINAL_20261004':'e1d4ab0b1de9069509e49a87ff296fdaed988fe8b552905293ed2d59b3580019','E_PUBLIC_GB55036_ORIGINAL_20261004':'2d54318955e35b4a81049f755505381c542a215ecc8cacd76eb2d9a91c6ff701'}
  for e,value in expected.items():
   x=read('evidence',e);self.assertEqual(x['snapshotSha256'],value);self.assertTrue(x['url'].startswith('https://js.119.gov.cn/'));self.assertIn('publicationLimits',x)
  self.assertEqual(len(F['semanticCases']),9)
  for x in F['semanticCases']:self.assertTrue(x['positive']);self.assertTrue(x['negative']);self.assertTrue(x['boundary'])
if __name__=='__main__':unittest.main()
