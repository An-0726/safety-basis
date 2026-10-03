"""Bounded training citation repair: exact data, history, scope, and fail-closed gate.

These regressions bind reviewed prose. They do not infer enterprise compliance or
pretend that hashes alone make an incorrect legal proposition correct.
"""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
KNOW=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools/v4'))
from canonical import content_hash
from field_profiles import ProfileContext
from release_gate_core import evaluate_release_gate
F=json.loads((Path(__file__).parent/'fixtures/training_citation_repair_20261003.json').read_text())
ASOF=date(2026,10,3)
BAD=F['badClauseId']; NAT=F['nationalClauseId']; JS=F['jiangsuClauseId']
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):return json.loads((ROOT/p).read_text())
def write(root,rel,obj):
 p=root/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False))
class TrainingCitationRepair(unittest.TestCase):
 def test_exact_entities_and_stable_ids(self):
  self.assertEqual(len(F['entities']),12);self.assertEqual(sum(len(r['modifiedFields']) for r in F['entities']),37)
  for r in F['entities']:
   with self.subTest(path=r['path']):
    got=read(r['path']);self.assertEqual(got,r['record']);self.assertEqual(got['id'],r['before']['id'])
    self.assertEqual(sha((ROOT/r['path']).read_bytes()),r['fileSha256'])
    self.assertEqual(sha(r['beforeFileText'].encode()),r['oldFileSha256'])
    replay=copy.deepcopy(r['before']);replay.update(r['after']);self.assertEqual(got,replay)
    self.assertEqual({k:got[k] for k in r['unchangedFields']},r['unchangedFields'])
 def test_full_quote_and_corrupt_history_preservation(self):
  for cid,q in F['canonicalQuotes'].items():self.assertEqual(read(f'knowledge/clauses/{cid}.json')['quote'],q)
  bad=read(f'knowledge/clauses/{BAD}.json');review=read(f'knowledge/reviews/clauses/{BAD}.json')
  self.assertEqual(bad['articlePath'],'二十二');self.assertTrue(bad['quote'].startswith('第七十二条'))
  self.assertEqual(bad['lifecycle'],'proposed');self.assertEqual(review['decision'],'rejected')
  self.assertEqual(read(f'knowledge/clauses/{JS}.json')['jurisdictionCode'],'CN-32')
  self.assertEqual(review['previousEntity']['lifecycle'],'active')
  self.assertEqual(review['previousReview']['decision'],'verified')
 def test_reviews_are_truthful_scoped_and_history_bound(self):
  self.assertEqual(len(F['reviews']),14)
  for r in F['reviews']:
   actual=read(r['path']);self.assertEqual(actual,r['record'])
   self.assertEqual(actual['historySha256'],content_hash(actual['previousReview']))
   self.assertEqual(actual['previousReviewFileSha256'],r['previousFileSha256'])
   ent=read(r['path'].replace('/reviews',''));self.assertEqual(actual['reviewedContentHash'],content_hash(ent))
   if ent.get('hazardId'):
    self.assertEqual(actual['contextHashes'],{'hazard':content_hash(read(f"knowledge/hazards/{ent['hazardId']}.json")),'clause':content_hash(read(f"knowledge/clauses/{ent['clauseId']}.json"))})
   if r['kind']=='substantive':
    self.assertEqual(actual['reviewedValues'],{p:ent[p[1:]] for p in actual['reviewedFields']})
    self.assertFalse(actual['reviewEvidence']['siteFactsVerified']);self.assertFalse(actual['reviewEvidence']['profileAdmission'])
   else:
    self.assertEqual(actual['decision'],'pending');self.assertEqual(actual['evidenceRefs'],[])
    self.assertEqual(actual['checkedAt'],actual['previousReview']['checkedAt'])
    self.assertFalse(actual['bindingMaintenance']['substantiveApplicabilityReviewed'])
 def test_exact_rebinding_and_no_bad_dependencies(self):
  for row in F['fiveLinks']:
   k=read(f"knowledge/links/{row['linkId']}.json")
   self.assertEqual(k['hazardId'],row['hazardId']);self.assertEqual(k['clauseId'],row['clauseId']);self.assertEqual(k['role'],'direct')
  for p in (KNOW/'links').glob('*.json'):self.assertNotEqual(json.loads(p.read_text()).get('clauseId'),BAD)
 def test_national_and_jiangsu_boundaries_are_preserved(self):
  for row in F['fiveLinks']:
   h=read(f"knowledge/hazards/{row['hazardId']}.json");k=read(f"knowledge/links/{row['linkId']}.json")
   if row['clauseId']==NAT:
    self.assertEqual(k['jurisdictionCode'],'CN');self.assertIn('第二十七条第一款',h['conditions']);self.assertIn('仅该条第二款列明',h['conditions'])
    self.assertIn('不得将考核要求扩展为所有行业一律取得安全培训合格证',h['conditions']);self.assertNotIn('六个月',h['conditions']);self.assertNotIn('江苏',h['conditions'])
   else:
    self.assertEqual(k['jurisdictionCode'],'CN-32')
    for token in ['江苏省行政区域内','矿山','金属冶炼','建筑施工','船舶修造','船舶拆解','运输单位','生产、经营、储存、装卸','主要负责人和安全生产管理人员']:self.assertIn(token,h['conditions'])
    self.assertNotIn('通用场所',h['places']);self.assertEqual(h['category'],'安全教育培训')
  new=read(f'knowledge/hazards/H_9F790C9B0EA34E59207BCCC1AD_2.json')
  for f in ['conditions','description','measures']:self.assertIn('自任职之日起六个月内',new[f])
  retrain=read(f'knowledge/hazards/H_9F790C9B0EA34E59207BCCC1AD_3.json')
  self.assertIn('已经考核合格',retrain['conditions']);self.assertIn('不自行设定统一再培训周期',retrain['conditions'])
 def test_historical_helpers_reject_unknown_mutation_and_preserve_unrelated_rows(self):
  from training_citation_fixture import pre_training_gate, pre_training_inventory, pre_training_source_hashes
  gate=evaluate_release_gate(KNOW,ASOF);original=copy.deepcopy(gate)
  old=pre_training_gate(gate)
  self.assertEqual(old.eligible_hazards,gate.eligible_hazards);self.assertEqual(old.eligible_links,gate.eligible_links)
  self.assertEqual(gate.links,original.links)
  for kid,row in gate.links.items():
   if kid not in {x['linkId'] for x in F['fiveLinks']}:self.assertEqual(old.links[kid],row)
  for mode in ['removed','wrong_clause']:
   bad=copy.deepcopy(gate);kid=F['fiveLinks'][0]['linkId']
   if mode=='removed':bad.eligible_links.remove(kid)
   else:bad.links[kid]['clauseId']='C_UNREVIEWED'
   with self.assertRaises(AssertionError):pre_training_gate(bad)
  unrelated={'knowledge/hazards/H_UNREVIEWED.json':'unexpected-bytes'}
  self.assertEqual(pre_training_source_hashes(unrelated),unrelated)
  row=F['entities'][0]
  with self.assertRaises(AssertionError):pre_training_source_hashes({row['path']:'0'*64})
  with self.assertRaises(AssertionError):pre_training_inventory('clauses',[(BAD,'active')])
  self.assertEqual(pre_training_inventory('clauses',[(BAD,'proposed'),('C_UNREVIEWED','proposed')]),sorted([(BAD,'active'),('C_UNREVIEWED','proposed')]))
 def snapshot(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name);ctx=ProfileContext(KNOW)
  for r in F['fiveLinks']:
   for key,obj in ctx.dependencies({'hazardId':r['hazardId'],'basisLinkIds':[r['linkId']]}).items():
    if key!='associationIds' and obj is not None:write(root,key+'.json',obj)
  for p in [f'clauses/{BAD}.json',f'reviews/clauses/{BAD}.json']:write(root,p,read('knowledge/'+p))
  return root
 def test_five_corrected_paths_pass_and_candidates_stay_excluded(self):
  gate=evaluate_release_gate(KNOW,ASOF)
  self.assertTrue({x['hazardId'] for x in F['fiveLinks']}<=gate.eligible_hazards)
  self.assertTrue({x['linkId'] for x in F['fiveLinks']}<=gate.eligible_links)
  self.assertFalse(gate.clauses[BAD]['ok'])
  for kid in ['K_84CD742E5092AF652C2CEF43','K_d63a0fe9faaed461738348e9']:self.assertNotIn(kid,gate.eligible_links)
  for hid in ['H_5B89D7164D2C4B6E983663B009','H_COM_CONSTRUCTION_BOX_PE','H_COM_SMOKE_WINDOW_MANUAL_INSTALL','H_COM_CYLINDER_WAREHOUSE_REGISTER','H_COM_HYDRANT_HOSE_ARRANGEMENT']:self.assertNotIn(hid,gate.eligible_hazards)
 def test_old_reviews_cannot_be_reused_after_repair(self):
  root=self.snapshot()
  for r in F['reviews']:
   if r['kind']=='substantive':write(root,r['path'].removeprefix('knowledge/'),r['record']['previousReview'])
  gate=evaluate_release_gate(root,ASOF)
  self.assertFalse({x['hazardId'] for x in F['fiveLinks']}&gate.eligible_hazards)
  self.assertFalse({x['linkId'] for x in F['fiveLinks']}&gate.eligible_links)
 def test_wrong_penalty_body_or_scope_tampering_fails_closed(self):
  # Intentionally bad records stay in disposable test copies. No re-review or
  # synthetic verified hash is authored to legalize any negative mutation.
  cases=[]
  for cid in [NAT,JS]:cases.append((f'clauses/{cid}.json','quote',F['canonicalQuotes'][BAD]))
  for r in F['fiveLinks']:
   if r['clauseId']==NAT:cases.append((f"links/{r['linkId']}.json",'clauseId',JS))
   else:
    cases.append((f"hazards/{r['hazardId']}.json",'conditions','适用于所有生产经营单位。'))
    cases.append((f"links/{r['linkId']}.json",'jurisdictionCode','CN'))
  cases.append(('hazards/H_9F790C9B0EA34E59207BCCC1AD_2.json','conditions','适用于江苏省内新任职人员，无任职时限。'))
  for path,field,bad in cases:
   with self.subTest(path=path,field=field):
    root=self.snapshot();obj=json.loads((root/path).read_text());obj[field]=bad;write(root,path,obj)
    gate=evaluate_release_gate(root,ASOF)
    if path.startswith('clauses/'):
     self.assertFalse(gate.clauses[obj['id']]['ok'])
     for row in F['fiveLinks']:
      if row['clauseId']==obj['id']:self.assertNotIn(row['linkId'],gate.eligible_links)
    elif path.startswith('hazards/'):self.assertNotIn(obj['id'],gate.eligible_hazards)
    else:self.assertNotIn(obj['id'],gate.eligible_links)
 def test_rebinding_back_to_quarantined_clause_never_passes(self):
  root=self.snapshot()
  for row in F['fiveLinks']:
   path=f"links/{row['linkId']}.json";k=json.loads((root/path).read_text());k['clauseId']=BAD;write(root,path,k)
  gate=evaluate_release_gate(root,ASOF)
  self.assertFalse({x['linkId'] for x in F['fiveLinks']}&gate.eligible_links)
if __name__=='__main__':unittest.main()
