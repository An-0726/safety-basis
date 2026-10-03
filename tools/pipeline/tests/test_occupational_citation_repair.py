"""Narrow Article 25 repair: official duty scope, quarantine and immutable history."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
ROOT=Path(__file__).resolve().parents[3]
KNOW=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate,gate_clause,gate_link
F=json.loads((Path(__file__).parent/'fixtures/occupational_citation_repair_20261003.json').read_text())
CAN=F['canonicalClauseId'];BAD=F['badClauseIds']
def read(kind,ident):return json.loads((KNOW/kind/(ident+'.json')).read_text())
def digest(raw):return hashlib.sha256(raw).hexdigest()
def norm(t):return re.sub(r'\s+','',t)
def scope_errors(h,k,n):
    errors=[]
    if k['clauseId']!=CAN:errors.append('noncanonical clause')
    if h['category']!='职业卫生':errors.append('wrong taxonomy')
    if h['conditions']!=k['applicability']:errors.append('scope mismatch')
    if '现场检查发现' in h['description']:errors.append('unverified site fact')
    if n==1:
        for field in ['title','description','conditions']:
            if '可能发生急性职业损伤' not in h[field] or '必要' not in h[field]:errors.append('acute/necessary scope')
        if '仅有职业病危害因素不自动满足' not in h['conditions']:errors.append('overbroad workplace')
        if '第一款' not in k['applicability']:errors.append('paragraph 1')
    if n==2:
        for field in ['title','description']:
            if '未配置防护设备或报警装置' not in h[field] or '未保证接触放射线的工作人员佩戴个人剂量计' not in h[field]:errors.append('negative obligation direction')
        for field in ['conditions','description']:
            if '放射工作场所' not in h[field] or '放射性同位素' not in h[field] or '运输、贮存' not in h[field]:errors.append('radiation scope')
        if '不以存在机械运动' not in h['conditions']:errors.append('mechanical prerequisite')
        if any(x in h['measures'] for x in ['试运行','联锁']):errors.append('mechanical remedy')
    if n==3:
        if '不扩展为所有普通设备设施' not in h['conditions']:errors.append('general equipment expansion')
        for term in ['职业病防护设备','应急救援设施','个人使用的职业病防护用品','用人单位']:
            if term not in h['conditions']:errors.append('paragraph 3 subject/object')
        if '未对' not in h['description'] or '或者未定期检测其性能和效果' not in h['description']:errors.append('maintenance negative direction')
    return errors
class OccupationalCitationRepairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.gate=evaluate_release_gate(KNOW,date(2026,10,3))
    def test_exact_eight_entities_and_stable_ids(self):
        self.assertEqual(len(F['entities']),8)
        for row in F['entities']:
            current=json.loads((ROOT/row['path']).read_text());expected=copy.deepcopy(row['before']);expected.update(row['after'])
            self.assertEqual(current,expected,row['path']);self.assertEqual(current['id'],row['before']['id'])
            self.assertEqual(digest((ROOT/row['path']).read_bytes()),row['fileSha256'])
            self.assertEqual(content_hash(current),row['contentHash'])
            self.assertEqual(digest(row['beforeFileText'].encode()),row['oldFileSha256'])
            self.assertEqual(json.loads(row['beforeFileText']),row['before'])
    def test_immutable_nine_old_reviews_and_hashes(self):
        self.assertEqual(len(F['reviews']),9)
        for row in F['reviews']:
            current=json.loads((ROOT/row['path']).read_text());self.assertEqual(current,row['record'])
            previous=json.loads(row['previousFileText']);self.assertEqual(current['previousReview'],previous)
            self.assertEqual(digest(row['previousFileText'].encode()),current['previousReviewFileSha256'])
            self.assertEqual(content_hash(previous),current['historySha256'])
            entity=json.loads((ROOT/row['path'].replace('/reviews','')).read_text())
            self.assertEqual(content_hash(entity),current['reviewedContentHash'])
            if current['entityType']=='link':self.assertEqual(current['contextHashes'],{'hazard':content_hash(read('hazards',entity['hazardId'])),'clause':content_hash(read('clauses',entity['clauseId']))})
    def test_whole_canonical_clause_reused_verbatim(self):
        c=read('clauses',CAN);self.assertEqual(c['quote'],F['completeQuote']);self.assertEqual(c['articlePath'],'第二十五条')
        self.assertEqual(c,read('reviews/clauses',CAN)['previousEntity']);self.assertTrue(self.gate.clauses[CAN]['ok'])
        self.assertEqual(c['quote'].count('用人单位'),3);self.assertNotIn('（四）',c['quote'])
    def test_three_paragraphs_have_exact_direct_links(self):
        for row in F['paragraphLinks']:
            h=read('hazards',row['hazardId']);k=read('links',row['linkId'])
            self.assertEqual(scope_errors(h,k,row['paragraph']),[])
            self.assertEqual(k['role'],'direct');self.assertIn(k['id'],self.gate.eligible_links);self.assertIn(h['id'],self.gate.eligible_hazards)
            self.assertIn('第'+['','一','二','三'][row['paragraph']]+'款',k['reason'])
    def test_corrupted_clauses_preserve_quote_and_have_zero_incoming_links(self):
        for cid in BAD:
            c=read('clauses',cid);review=read('reviews/clauses',cid)
            self.assertEqual(c['lifecycle'],'superseded');self.assertEqual(review['decision'],'rejected');self.assertFalse(self.gate.clauses[cid]['ok'])
            for field in ['id','quote','articlePath','lawVersionId','sourceUrl']:self.assertEqual(c[field],review['previousEntity'][field])
            self.assertTrue(c['quote'].startswith('第二十五条规定的；'));self.assertIn('（八）',c['quote'])
            for p in KNOW.rglob('*.json'):
                if '/reviews/' not in str(p) and p.name!=cid+'.json':self.assertNotIn(cid,p.read_text(),str(p))
    def test_quarantine_cannot_be_revived_by_hash_refresh_alone(self):
        for cid in BAD:
            c=read('clauses',cid);r=read('reviews/clauses',cid);r['decision']='verified'
            self.assertFalse(gate_clause(c,r,True,True)[0])
            c['lifecycle']='active';r['decision']='rejected';r['reviewedContentHash']=content_hash(c)
            self.assertFalse(gate_clause(c,r,True,True)[0])
    def test_negative_old_penalty_link_is_blocked_even_with_new_bindings(self):
        for row in F['paragraphLinks']:
            k=read('links',row['linkId']);h=read('hazards',row['hazardId']);c=read('clauses',BAD[0]);k['clauseId']=c['id'];r=read('reviews/links',k['id']);r['reviewedContentHash']=content_hash(k);r['contextHashes']={'hazard':content_hash(h),'clause':content_hash(c)}
            law=read('laws',read('law-versions',c['lawVersionId'])['lawId'])
            self.assertFalse(gate_link(k,r,h,c,law,False)[0]);self.assertIn('noncanonical clause',scope_errors(h,k,row['paragraph']))
    def test_negative_acute_scope_broadening_and_necessary_qualifier(self):
        row=F['paragraphLinks'][0];h=read('hazards',row['hazardId']);k=read('links',row['linkId'])
        for old,new in [('可能发生急性职业损伤','存在职业病危害因素'),('必要','')]:
            bad=copy.deepcopy(h);bad['conditions']=bad['conditions'].replace(old,new);self.assertTrue(scope_errors(bad,k,1))
    def test_negative_radiation_normal_wearing_is_not_hazard(self):
        row=F['paragraphLinks'][1];h=read('hazards',row['hazardId']);k=read('links',row['linkId'])
        for field in ['title','description']:
            bad=copy.deepcopy(h);bad[field]=bad[field].replace('未保证','保证');self.assertIn('negative obligation direction',scope_errors(bad,k,2))
    def test_negative_radiation_missing_one_device_is_sufficient(self):
        row=F['paragraphLinks'][1];h=read('hazards',row['hazardId']);k=read('links',row['linkId'])
        for field in ['title','description']:
            bad=copy.deepcopy(h);bad[field]=bad[field].replace('防护设备或报警装置','防护设备和报警装置');self.assertIn('negative obligation direction',scope_errors(bad,k,2))
    def test_negative_mechanical_taxonomy_and_trial_run(self):
        row=F['paragraphLinks'][1];h=read('hazards',row['hazardId']);k=read('links',row['linkId'])
        for field,value in [('category','机械与设备安全'),('measures','必要时试运行验证')]:
            bad=copy.deepcopy(h);bad[field]=value;self.assertTrue(scope_errors(bad,k,2))
    def test_negative_general_equipment_extension(self):
        row=F['paragraphLinks'][2];h=read('hazards',row['hazardId']);k=read('links',row['linkId']);h['conditions']='适用于所有普通设备设施'
        self.assertTrue(scope_errors(h,k,3))
    def test_current_source_provenance_and_no_site_admission(self):
        for row in F['reviews']:
            r=row['record'];s=r['reviewEvidence'];self.assertEqual(s['checkedAt'],'2026-10-03');self.assertEqual(s['effectiveDate'],'2018-12-29');self.assertFalse(s['siteFactsVerified']);self.assertFalse(s['profileAdmission'])
            self.assertIn('samr.gov.cn',s['statusSourceUrl']);self.assertIn('wjw.beijing.gov.cn',s['officialSourceUrl'])
    def test_public_hazard_link_set_inheritance_at_both_dates(self):
        for day,expected in F['baselineGate'].items():
            gate=self.gate if day=='2026-10-03' else evaluate_release_gate(KNOW,date.fromisoformat(day))
            self.assertEqual(content_hash(sorted(gate.eligible_hazards)),expected['hazardIdsHash']);self.assertEqual(content_hash(sorted(gate.eligible_links)),expected['linkIdsHash'])
    def test_no_new_entity_or_canonical_identity_mutation(self):
        self.assertEqual({r['path'].split('/')[1] for r in F['entities']},{'hazards','links','clauses'})
        self.assertEqual({r['path'].split('/')[2][:-5] for r in F['entities'] if '/clauses/' in r['path']},set(BAD))
        self.assertEqual(len(list((KNOW/'clauses').glob('*.json'))),self.gate.counts['clauses'])
    def test_historical_inverse_rejects_unexpected_source_bytes(self):
        from occupational_citation_fixture import pre_occupational_source_bytes
        for row in F['entities']:
            raw=(ROOT/row['path']).read_bytes()
            self.assertEqual(pre_occupational_source_bytes(row['path'],raw),row['beforeFileText'].encode())
            with self.assertRaises(AssertionError):pre_occupational_source_bytes(row['path'],raw+b' ')
        self.assertEqual(pre_occupational_source_bytes('knowledge/hazards/H_UNKNOWN.json',b'unknown'),b'unknown')
    def test_historical_inverse_rejects_unexpected_lifecycle(self):
        from occupational_citation_fixture import pre_occupational_inventory
        for cid in BAD:
            self.assertEqual(pre_occupational_inventory('clauses',[(cid,'superseded')]),[(cid,'active')])
            with self.assertRaises(AssertionError):pre_occupational_inventory('clauses',[(cid,'active')])
        self.assertEqual(pre_occupational_inventory('clauses',[('C_UNKNOWN','proposed')]),[('C_UNKNOWN','proposed')])
    def test_historical_inverse_rejects_unexpected_gate_and_keeps_unknown(self):
        from occupational_citation_fixture import pre_occupational_gate
        for kid,row in F['gateLinkTransitions'].items():
            bad=copy.deepcopy(self.gate);bad.links[kid]['clauseId']='C_UNREVIEWED'
            with self.assertRaises(AssertionError):pre_occupational_gate(bad)
        changed=copy.deepcopy(self.gate);changed.links['K_UNKNOWN']={'ok':False};changed.eligible_hazards.add('H_UNKNOWN')
        prior=pre_occupational_gate(changed);self.assertEqual(prior.links['K_UNKNOWN'],{'ok':False});self.assertIn('H_UNKNOWN',prior.eligible_hazards)
if __name__=='__main__':unittest.main()
