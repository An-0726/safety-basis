"""Necessary-clause, scope and conservation checks for GB50054/JGJ91 repairs."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest
from public_technical_citation_fixture import F, pre_technical_source_bytes, pre_technical_gate, pre_technical_manifest
from recovery_cohort_fixture import pre_recovery_source_bytes, pre_recovery_gate
ROOT = Path(__file__).resolve().parents[3]
from official_clause_cohort_fixture import pre_official_repo_root
# Preserve the dated cohort against its exact, fail-closed batch predecessor.
ROOT = pre_official_repo_root(ROOT)
KNOW = ROOT/'knowledge'
sys.path.insert(0, str(ROOT/'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate
from field_profiles import public_projection
sha = lambda b: hashlib.sha256(b).hexdigest()
def read(kind, ident):
    path = KNOW/kind/(ident+'.json')
    return json.loads(pre_recovery_source_bytes(path.relative_to(ROOT).as_posix(), path.read_bytes()))
HIDS = ['H057','H056','H_FE6C8CE7D9D74815847BCF72A7','H_B57B762BDB8149F4BACB629CFF','H_7A03BD4501C948B78EA50A2733','H_701AAE9385E74703A71396776E']

class PublicTechnicalCitationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = pre_recovery_gate(evaluate_release_gate(KNOW,date(2026,10,3)))

    def test_every_changed_source_is_exact_and_old_bytes_are_recoverable(self):
        self.assertEqual(len(F['records']),50)
        for path,row in F['records'].items():
            raw=pre_recovery_source_bytes(path,(ROOT/path).read_bytes())
            self.assertEqual(sha(raw),row['afterSha256'],path)
            self.assertEqual(raw.decode(),row['afterFileText'],path)
            expected=None if row['beforeFileText'] is None else row['beforeFileText'].encode()
            self.assertEqual(pre_technical_source_bytes(path,raw),expected)
            with self.assertRaises(AssertionError):pre_technical_source_bytes(path,raw+b' ')

    def test_no_unrelated_knowledge_was_modified_or_removed(self):
        rows={}
        for p in KNOW.rglob('*'):
            if not p.is_file():continue
            path=p.relative_to(ROOT).as_posix()
            if path in F['records']:continue
            raw=pre_recovery_source_bytes(path,p.read_bytes())
            if raw is not None:rows[path]=sha(raw)
        self.assertEqual(len(rows),F['unchangedKnowledge']['count'])
        self.assertEqual(sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),F['unchangedKnowledge']['sha256'])

    def test_all_old_reviews_and_entity_ids_are_preserved(self):
        for path,row in F['records'].items():
            if '/reviews/' not in path:continue
            rev=json.loads(row['afterFileText']);old=json.loads(row['beforeFileText']) if row['beforeFileText'] else None
            if old is not None:
                self.assertEqual(rev['previousReview'],old,path)
                self.assertEqual(rev['previousReviewFileSha256'],row['beforeSha256'])
                self.assertEqual(rev['historySha256'],content_hash(old))
            ent=read(path.split('/')[2],rev['entityId'])
            self.assertEqual(rev['reviewedContentHash'],content_hash(ent))
            if rev['entityType']=='link':
                self.assertEqual(rev['contextHashes']['hazard'],content_hash(read('hazards',ent['hazardId'])))
                self.assertEqual(rev['contextHashes']['clause'],content_hash(read('clauses',ent['clauseId'])))
            if 'reviewedFields' in rev:
                self.assertEqual(rev['reviewedValues'],{p:ent[p[1:]] for p in rev['reviewedFields']})
                self.assertFalse(rev['reviewEvidence']['siteFactsVerified'])
                self.assertFalse(rev['reviewEvidence']['profileAdmission'])

    def test_gb50054_is_heavy_dust_heat_dissipation_not_explosion_only(self):
        h=read('hazards','H057');k=read('links','K_7D5C8F3ACEC4C1E8E4554F')
        self.assertEqual(h['category'],'电气安全')
        self.assertIn('交流、工频1000V及以下',h['conditions'])
        self.assertIn('不以粉尘可燃或存在爆炸危险为前提',h['conditions'])
        self.assertIn('少量表面浮尘不自动',h['conditions'])
        self.assertEqual(k['applicability'],h['conditions'])
        self.assertEqual(k['role'],'direct')
        self.assertNotIn('绝缘',h['description']+h['measures'])
        c=read('clauses','C_GB50054_7_1_2_4')
        self.assertTrue(c['sourceUrl'].endswith('P020260916651119858336.pdf'))
        old=read('reviews/clauses',c['id'])['previousEntity']
        self.assertEqual(c['quote'],old['quote'])

    def test_fire_law_reference_is_supporting_and_has_no_explosion_predicate(self):
        k=read('links','K_f3c46052650eaf7fbe06537e')
        self.assertEqual(k['role'],'supporting');self.assertIn('不能单独',k['applicability'])
        r=read('reviews/links',k['id'])
        self.assertEqual(r['previousReview']['reasonCodes'][-1],'DUST_EXPLOSION_STANDARD_REQUIRED')
        self.assertNotIn('reasonCodes',r)
        self.assertIn(k['id'],self.gate.eligible_links)

    def test_jgj_exact_clauses_do_not_keep_added_or_hybrid_requirements(self):
        a=read('clauses','C_JGJ91_10_1_7')['quote'];self.assertNotIn('防雨',a);self.assertIn('1m或1m以上',a)
        b=read('clauses','C_JGJ91_10_2_5')['quote'];self.assertIn('应不渗漏、耐压、耐温、耐腐蚀',b);self.assertIn('维修明露管道',b)
        c=read('clauses','C_JGJ91_10_2_6')['quote'];self.assertIn('金属标记、模板印刷、盖印或粘着性标志',c);self.assertIn('施工中宜',c)
        self.assertNotIn('介质名称',c);self.assertNotIn('流向',c)
        d=read('clauses','C_JGJ91_10_2_7')['quote'];self.assertTrue(d.startswith('埋地敷设'));self.assertNotIn('阻火器',d)
        self.assertIn('不应小于当地冻土层厚度',d);self.assertIn('不宜小于0.70m',d);self.assertEqual(len(d.splitlines()),6)
        flame=read('clauses','C_JGJ91_10_4_3')['quote']
        self.assertEqual(flame,'可燃气体管道连接用气设备支管应设置阻火器。')
        self.assertNotIn('放空管',flame);self.assertNotIn('等安全控制装置',flame)

    def test_jgj_hazards_have_design_scope_and_separate_failure_branches(self):
        for hid in HIDS[1:]:
            h=read('hazards',hid)
            self.assertIn('新建、扩建、改建',h['conditions']);self.assertIn('科研建筑设计',h['conditions'])
            self.assertEqual(h['mode'],'conditional');self.assertNotIn('通用场所',h['places'])
            self.assertNotIn('现场检查发现',h['description']);self.assertIn(hid,self.gate.eligible_hazards)
        bad=read('hazards','H_B57B762BDB8149F4BACB629CFF')
        self.assertNotIn('未见渗漏',bad['measures']);self.assertNotIn('未不渗漏',bad['description'])
        self.assertIn('或者',bad['description'])
        mark=read('hazards','H_7A03BD4501C948B78EA50A2733')
        self.assertIn('宜采用',mark['conditions']);self.assertIn('不能仅因',mark['conditions'])
        link=read('links','K_XLSX_WEB_H_701AAE9385E74703A71396776E')
        self.assertEqual(link['clauseId'],'C_JGJ91_10_4_3')

    def test_source_provenance_and_status_roles_are_explicit(self):
        gb=read('evidence','E_GB50054_DUST_SCOPE_20261003')
        self.assertEqual(gb['snapshotSha256'],'25e8a883e36ca7545f54a822842b239100997577e42240fb4516f28c0f8269fe')
        self.assertIn('sourceOperatorUrl',gb)
        j=read('evidence','E_JGJ91_ORIGINAL_CLAUSES_20261003')
        self.assertEqual(j['snapshotSha256'],'307103d4eb66fd3fd216c56e0d73093f6a332b08f2527be10aab90d6b521deda')
        self.assertEqual(j['originalAnnouncement']['number'],'住房和城乡建设部2019年第211号')
        self.assertIn('不是标准发布机关',j['currentnessResult'])
        self.assertEqual(len(j['currentnessEvidence']),2)
        self.assertIn('20260826',j['currentnessEvidence'][1]['url'])
        self.assertIn('不因该访问缺口断言标准已经废止',j['statusLimits'])

    def test_pending_fallback_is_not_resigned_into_publication(self):
        kid='K_99a2fb6f2ff4a9ae96895dd2';k=read('links',kid);r=read('reviews/links',kid)
        self.assertEqual(k['lifecycle'],'proposed');self.assertEqual(r['decision'],'pending')
        self.assertEqual(r['checkedAt'],r['previousReview']['checkedAt'])
        self.assertFalse(r['bindingMaintenance']['substantiveApplicabilityReviewed'])
        self.assertNotIn(kid,self.gate.eligible_links)

    def test_four_date_gate_has_no_unrelated_membership_change(self):
        for day,delta in F['gateSnapshots'].items():
            g=pre_recovery_gate(evaluate_release_gate(KNOW,date.fromisoformat(day)))
            self.assertEqual(len(g.eligible_hazards),delta['counts']['hazards'])
            self.assertEqual(len(g.eligible_links),delta['counts']['links'])
            for name in ['hazardsAdded','hazardsRemoved','linksAdded','linksRemoved']:self.assertEqual(delta[name],[])
            before=pre_technical_gate(g)
            self.assertEqual(before.eligible_hazards,g.eligible_hazards)
            self.assertEqual(before.eligible_links,g.eligible_links)

    def test_exact_inverse_rejects_drift_without_hiding_unknown_changes(self):
        original=copy.deepcopy(self.gate);old=pre_technical_gate(self.gate)
        self.assertEqual(self.gate,original)
        for kid,row in F['gateSnapshots']['2026-10-03']['changedLinks'].items():
            self.assertEqual(old.links[kid],row['before'])
            changed=copy.deepcopy(self.gate);changed.links[kid]['clauseId']='C_UNREVIEWED'
            with self.assertRaises(AssertionError):pre_technical_gate(changed)
        changed=copy.deepcopy(self.gate);changed.eligible_hazards.add('H_UNKNOWN')
        self.assertIn('H_UNKNOWN',pre_technical_gate(changed).eligible_hazards)
        self.assertEqual(pre_technical_source_bytes('unknown',b'unexpected'),b'unexpected')
        m=read('','manifest');before=pre_technical_manifest(m)
        self.assertEqual(before,json.loads(F['records']['knowledge/manifest.json']['beforeFileText']))
        m['counts']['evidence']+=1
        self.assertEqual(pre_technical_manifest(m)['counts']['evidence'],before['counts']['evidence']+1)

    def test_jiangsu_shared_clause_and_all_four_consumers_keep_region(self):
        cid='C_462D38828DEBA46C8E23C177D2'
        self.assertEqual(read('clauses',cid)['jurisdictionCode'],'CN-32')
        kids=['K_5A0522BE823232ED4D92A276','K_XLSX_FT_515B4C8C1BAAA974D0737B8E','K_XLSX_FT_79114EC5A4F800DD8C81F752','K_XLSX_FT_A48D9B4D27EAC4160CBAC418']
        for kid in kids:
            k=read('links',kid)
            self.assertEqual(k['clauseId'],cid);self.assertEqual(k['jurisdictionCode'],'CN-32')
            self.assertIn('江苏省',k['applicability']);self.assertIn(kid,self.gate.eligible_links)
        k=read('links',kids[0]);self.assertIn('仅核第三十条第一款第（三）、（四）项',k['applicability'])
        self.assertIn('仅督促整改不到位不自动',k['applicability'])
        for kid in kids[1:]:
            r=read('reviews/links',kid)
            self.assertEqual(r['checkedAt'],r['previousReview']['checkedAt'])
            self.assertEqual(r['dependencyReview']['changedFields'],['/jurisdictionCode'])

    def test_h061_major_recheck_changes_only_the_unselected_dependency_binding(self):
        from field_profiles import ProfileContext
        path='knowledge/major-criteria/v1/catalog.json'
        old=json.loads(F['records'][path]['beforeFileText']);new=json.loads(pre_recovery_source_bytes(path,(ROOT/path).read_bytes()))
        selected=next(a for d in new['standards'] for a in d['topicLinks'] if a['hazardId']=='H061')
        before=next(a for d in old['standards'] for a in d['topicLinks'] if a['hazardId']=='H061')
        self.assertEqual(selected['linkId'],'K_7634A863A8C4CBA1D77F3A30')
        self.assertEqual(selected['clauseId'],'C_B9AF8F868C912A61F007845D84')
        expected=ProfileContext(KNOW).fingerprint({'hazardId':'H061','basisLinkIds':[selected['linkId']]})
        self.assertEqual(selected['dependencyFingerprint'],expected)
        selected['dependencyFingerprint']=before['dependencyFingerprint']
        self.assertEqual(new,old)
        k=read('links',selected['linkId']);self.assertEqual(k['jurisdictionCode'],'CN')
        self.assertIn('或者未定期',read('clauses',selected['clauseId'])['quote'])

    def test_all_twenty_five_profiles_remain_without_new_review(self):
        p=public_projection(KNOW,as_of=date(2026,10,3))
        self.assertEqual(len(p['public']['records']),25)
        self.assertEqual(p['inventory']['excludedProfiles'],[])
        self.assertFalse(any('field-profile' in path for path in F['records']))
        self.assertEqual([p for p in F['records'] if 'major-criteria' in p], ['knowledge/major-criteria/v1/catalog.json'])

if __name__=='__main__':unittest.main()
