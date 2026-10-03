"""Pinned scope and date regressions for the six independently reviewed checks.

Text assertions preserve reviewed boundaries; they do not automate field judgment.
"""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from common_hazards_fixture import (FIXTURE, ADDED_IDS, ADMITTED_IDS,
                                    pre_common_ids, pre_common_inventory,
                                    pre_common_manifest, pre_common_gate)

ROOT = Path(__file__).resolve().parents[3]
K = ROOT / 'knowledge'
sys.path.insert(0, str(ROOT / 'tools/v4'))
from canonical import content_hash
from release_gate_core import evaluate_release_gate, gate_hazard_content, gate_link

def load(kind, ident):
    return json.loads((K / kind / (ident + '.json')).read_text())

HIDS = ['H_46768_5_8_6', 'H_46768_5_10_2', 'H_46768_6_2_6',
        'H_GBT13869_REMOVED_POWER_END', 'H_GBT13869_RESTART_AFTER_STORAGE', 'H004']

class CommonHazardsBoundedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = evaluate_release_gate(K, date(2026,10,3))
        cls.review = json.loads((ROOT/'docs/common-hazards-bounded-20261003.json').read_text())

    def test_six_bounded_checks_are_eligible_at_current_snapshot(self):
        self.assertEqual(len(set(HIDS)), 6)
        for hid in HIDS:
            self.assertIn(hid, self.gate.eligible_hazards)
            self.assertIn('K_COMMON_'+hid,self.gate.eligible_links)

    def test_new_entities_and_reuse_are_counted_separately(self):
        self.assertEqual(self.review['counts'],dict(newHazards=5,existingCandidateNarrowedAndAdmitted=1,newClauses=2,reusedDirectClauses=3,directLinks=6,supportingLinks=3))
        self.assertEqual(sum(d['hazardAction']=='reuse_stable_id_and_narrow_definition' for d in self.review['decisions']),1)
        self.assertEqual(load('reviews/hazards','H004')['priorHazardDefinition']['title'],'安全出口无标识且上锁')

    def test_final_hashes_and_link_contexts_are_bound(self):
        for d in self.review['decisions']:
            h,c,k=load('hazards',d['hazardId']),load('clauses',d['clauseId']),load('links',d['linkId'])
            self.assertEqual(d['definitionHash'],content_hash(h))
            self.assertEqual(d['clauseHash'],content_hash(c))
            self.assertEqual(d['linkHash'],content_hash(k))
            r=load('reviews/links',d['linkId'])
            self.assertEqual(r['contextHashes'],{'hazard':content_hash(h),'clause':content_hash(c)})

    def test_all_confined_space_direct_links_have_scope_exclusions(self):
        for hid in HIDS[:3]:
            for txt in [load('hazards',hid)['conditions'],load('links','K_COMMON_'+hid)['applicability']]:
                for s in ['未被设计为固定工作场所','危险化学品生产、经营（带储存）企业','化工及医药企业','船舶','普通封闭房间不因封闭即适用']:
                    self.assertIn(s,txt)

    def test_point_sampling_keeps_both_short_distance_exceptions(self):
        c=load('clauses','C_46768_5_8_6')['quote']
        self.assertIn('竖向距离不足2m',c)
        self.assertIn('上、下2个点',c)
        self.assertIn('横向距离不足2m',c)
        self.assertIn('远端点应选取最远处',c)
        h=load('hazards','H_46768_5_8_6')
        self.assertIn('不把本条机械套到第6.2.3条作业中的实时监测',h['conditions'])

    def test_cross_references_are_supporting_and_stage_specific(self):
        self.assertEqual(len(self.review['supportingLinkIds']),3)
        for kid in self.review['supportingLinkIds']:
            k=load('links',kid)
            self.assertEqual(k['role'],'supporting')
            self.assertIn('本关联仅限',k['applicability'])
            self.assertIn(kid,self.gate.eligible_links)
        self.assertIn('不能仅以人员尚未进入排除作业前通风要求',load('hazards','H_46768_5_10_2')['conditions'])

    def test_interruption_sign_only_does_not_become_closure_defect(self):
        h=load('hazards','H_46768_6_2_6')
        self.assertIn('不能仅凭缺少警示标志或入口处于开启状态判定',h['description'])
        self.assertIn('仅缺安全警示不单独命中本H',h['conditions'])
        self.assertIn('设置警示标志',load('clauses','C_46768_6_2_6')['quote'])

    def test_electrical_chapter_is_shared_complete_and_recommendatory(self):
        c=load('clauses','C_GBT13869_6')
        self.assertEqual(c['articlePath'],'第6章')
        self.assertEqual(len(c['quote'].splitlines()),5)
        self.assertTrue(c['quote'].startswith('6 用电产品的维修\n'))
        for hid in HIDS[3:5]:
            h=load('hazards',hid)
            self.assertIn('推荐性用电安全技术要求检查',h['description'])
            k=load('links','K_COMMON_'+hid)
            self.assertEqual(k['clauseId'],'C_GBT13869_6')
            self.assertIn('交流1000 V及以下、直流1500 V及以下',k['applicability'])
        self.assertIn('不能擅填3个月/6个月',load('hazards',HIDS[4])['conditions'])

    def test_2017_electrical_basis_expires_on_replacement_day(self):
        for day,expected in [(date(2026,10,2),True),(date(2027,1,31),True),(date(2027,2,1),False)]:
            gate=evaluate_release_gate(K,day)
            for hid in HIDS[3:5]: self.assertEqual(hid in gate.eligible_hazards,expected)
            for hid in HIDS[:3]+HIDS[5:]: self.assertIn(hid,gate.eligible_hazards)
        self.assertEqual(load('law-versions','LV_STD_GBT13869_2017')['endDate'],'2027-02-01')

    def test_door_last_sentence_scope_and_distinct_sign_types(self):
        h=load('hazards','H004')
        self.assertIn('住宅户门',h['conditions'])
        self.assertIn('不包含该条前两句',h['conditions'])
        self.assertIn('门内明显标识不等同灯光疏散指示标志',h['conditions'])
        self.assertIn('仅存在正常刷卡方式或锁具不证明功能不合格',h['conditions'])
        self.assertIn('或标识',h['title'])
        self.assertTrue(h['note'].startswith('H004沿用既有稳定ID'))
        self.assertIn('不作为本条当前适用条件',h['note'])
        self.assertNotIn('应确认该门确为安全出口',h['note'])
        self.assertIn('应确认该门确为安全出口',load('reviews/hazards','H004')['priorHazardDefinition']['note'])

    def test_removed_source_condition_breaks_hash_binding(self):
        hid=HIDS[0]
        h=load('hazards',hid)
        r=load('reviews/hazards',hid)
        h['conditions']='任何封闭房间'
        self.assertFalse(gate_hazard_content(h,r)[0])

    def test_edited_link_scope_breaks_binding_and_changed_hazard_breaks_context(self):
        hid=HIDS[-1]
        h=load('hazards',hid); k=load('links','K_COMMON_'+hid); c=load('clauses',k['clauseId']); r=load('reviews/links',k['id'])
        altered=copy.deepcopy(k);altered['applicability']='任何门'
        self.assertFalse(gate_link(altered,r,h,c,None,True)[0])
        h['description']='仅有锁具即不合格'
        self.assertFalse(gate_link(k,r,h,c,None,True)[0])

    def test_historical_projection_hides_only_fixed_reviewed_ids(self):
        self.assertEqual(pre_common_ids('hazards',set(HIDS)|{'H_UNEXPECTED'}),{'H004','H_UNEXPECTED'})
        self.assertEqual(pre_common_inventory('hazards',[('H004','active'),('H_UNEXPECTED','active')]),
                         [('H004','proposed'),('H_UNEXPECTED','active')])
        g=SimpleNamespace(eligible_hazards=set(HIDS)|{'H_UNEXPECTED'},
                          eligible_links=set(ADDED_IDS['links'])|{'K_UNEXPECTED'},links={})
        p=pre_common_gate(g)
        self.assertEqual(p.eligible_hazards,{'H_UNEXPECTED'})
        self.assertEqual(p.eligible_links,{'K_UNEXPECTED'})
        self.assertIn('H004',g.eligible_hazards)

    def test_historical_manifest_projection_keeps_unknown_increment(self):
        actual=json.loads((K/'manifest.json').read_text());original=copy.deepcopy(actual)
        old=pre_common_manifest(actual)
        self.assertEqual(old['counts']['hazards'],actual['counts']['hazards']-5)
        self.assertEqual(old['lifecycle']['active'],actual['lifecycle']['active']-6)
        self.assertEqual(old['lifecycle']['proposed'],actual['lifecycle']['proposed']+1)
        actual['counts']['evidence']+=1
        self.assertEqual(pre_common_manifest(actual)['counts']['evidence'],old['counts']['evidence']+1)
        self.assertEqual(original,json.loads((K/'manifest.json').read_text()))

    def test_cohort_fixture_pins_exact_admitted_and_supporting_ids(self):
        self.assertEqual(set(FIXTURE['admittedHazardIds']),set(HIDS))
        self.assertEqual(ADDED_IDS['hazards'],set(HIDS)-{'H004'})
        self.assertEqual(ADDED_IDS['clauses'],{'C_GBT13869_6','C_GB55037_7_1_7'})
        self.assertEqual(ADDED_IDS['links'],{d['linkId'] for d in self.review['decisions']}|set(self.review['supportingLinkIds']))
        self.assertEqual(load('reviews/hazards','H004')['priorHazardDefinition'],FIXTURE['priorH004'])

if __name__ == '__main__': unittest.main()
