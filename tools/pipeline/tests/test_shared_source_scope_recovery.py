"""Current 27-rule source/scope regression, not an automated site adjudicator."""
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[3]
K=ROOT/'knowledge'
sys.path.insert(0,str(ROOT/'tools/v4'))
from release_gate_core import evaluate_release_gate
J=lambda p:json.loads(p.read_text())

class SharedSourceScopeRecoveryTests(unittest.TestCase):
 def test_exact_reviewed_dispositions_and_no_false_clause_fallback(self):
  report=J(ROOT/'docs/SHARED_SOURCE_RECOVERY_20261004.json')
  gate=evaluate_release_gate(K,date(2026,10,4))
  approval=J(ROOT/'docs/SHARED_SOURCE_INDEPENDENT_REVIEW_20261004.json')
  reviewed_ids={x['hazardId'] for x in approval['perHazardDecisions']}
  actual_ids=[x['hazardId'] for x in report['actions']]
  self.assertEqual(len(actual_ids),27)
  self.assertEqual(len(set(actual_ids)),27)
  self.assertEqual(set(actual_ids),reviewed_ids)
  self.assertEqual({x['disposition'] for x in report['actions']},{'exact_source_rebind','withdraw_current_direct_review'})
  self.assertEqual(sum(x['disposition']=='exact_source_rebind' for x in report['actions']),21)
  self.assertEqual(sum(x['disposition']=='withdraw_current_direct_review' for x in report['actions']),6)
  for row in report['actions']:
   self.assertEqual(row['hazardId'] in gate.eligible_hazards,row['disposition']=='exact_source_rebind',row['hazardId'])
   required={f'knowledge/{kind}/{row[key]}.json' for kind,key in [('hazards','hazardId'),('links','linkId'),('clauses','clauseId')]}
   required|={path.replace('knowledge/','knowledge/reviews/',1) for path in list(required)}
   self.assertEqual(set(row['finalContentBindings']),required)
   for path,digest in row['finalContentBindings'].items():
    self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),digest,path)
  self.assertFalse(any(v.get('ok') and v.get('clauseId')=='C_GB15577_6_1' for v in gate.links.values()))
 def test_sixteen_positive_field_contracts_preserve_negative_semantic_boundaries(self):
  cases=[]
  def case(id,hid,scenario,condition,result):
   cases.append((id,hid,scenario,condition,result))
  h=lambda id:J(K/'hazards'/f'{id}.json');c=lambda id:J(K/'clauses'/f'{id}.json')
  ha=h('H_AA7C48BCF0E6458484759F407B');case('layout_substation_only',ha['id'],'普通产尘车间，并非总变电站。','总变电站' in ha['conditions'] and '不泛化' in ha['conditions'],'不得套用总变电站专属风向判据。')
  q=c('C_GB50187_4_4_5')['quote'];case('layout_two_wind_relations',ha['id'],'以粉尘/腐蚀性污染源的冬季上风侧要求替换全年最小频率下风侧，或把水雾上风侧写成下风侧。','全年最小频率风向的下风侧' in q and '冬季盛行风向的上风侧' in q,'两类污染源及不同风向条件不得互换。')
  hc=h('H_C3B24EEDD61145A691A38B0414');case('compressed_air_special_scope',hc['id'],'井下/洞内站或非所列电力驱动压缩机设计。','不适用于井下、洞内' in hc['conditions'] and '42MPa' in hc['conditions'] and '电力驱动' in hc['conditions'],'不直接纳入本条限定设计范围。')
  case('compressed_air_recommendation',hc['id'],'仅未采用年最小频率风向下风侧，未核技术经济方案和设计条件。','原文中为“宜”' in hc['conditions'] and '不得仅凭' in hc['conditions'] and '并宜位于' in c('C_GB50029_2_0_1')['quote'],'不得单凭未采用推荐位置宣布违反强制性条文。')
  for hid in ['H_2870FFD9678642F4993A3CE571','H_B405711EED23418BAC72F90645','H_BFA0B7A7E308410DB3CC9358AB']:
   x=h(hid);case('gbz_design_scope_'+hid,hid,'任意既有企业在用场所，没有建设项目卫生设计/职业病危害评价触发。','卫生设计及职业病危害评价' in x['conditions'] and '不得将' in x['conditions'],'不得泛化为所有既有企业无条件粉尘防爆判据。')
  x=h('H_2870FFD9678642F4993A3CE571');case('gbz_enclosure_not_hood_substitution',x['id'],'仅称设有吸风罩，但产尘设备仍未密闭。','采取密闭措施' in x['measures'] and '吸风罩' not in x['measures'],'罩不能替代本项明确密闭义务。')
  q=c('C_GBZ1_6_1_1_3')['quote'];case('gbz_wet_condition','H_BFA0B7A7E308410DB3CC9358AB','粉尘性质/工艺不适合湿式作业。','生产工艺和粉尘性质可采取湿式作业的' in q and '当湿式作业仍不能满足卫生要求时' in q,'不能把原条改写成所有粉尘一律加水；也不能用湿法条件删除局排要求。')
  case('gbz_complete_mobile_tail','H_B405711EED23418BAC72F90645','删掉完整条文的移动扬尘/排毒设备最后一句。','对移动的扬尘和逸散毒物的作业' in c('C_GBZ1_6_1_1_2')['quote'],'完整C应保留后句，H仅消费前两句并不允许截断C。')
  for hid in ['H_1B2F6A143A9E492DBA2A246473','H_417B030F12A14923A978E4DAB2','H_6459FF72A542499FBB3E0F70FC']:
   x=h(hid);case('hj_adsorption_guidance_'+hid,hid,'非工业有机废气常压吸附治理工程，或把指导性技术项直接当普遍法定违法。','常压吸附' in x['conditions'] and '指导性文件' in x['conditions'],'不得跨工程范围、不得把指导性文件泛化为普遍法定义务。')
  case('valve_recommendation','H_CD6D8392BC7E40A787BD44D82A','室外干式除尘器未采用进风管隔爆阀，但尚未核其他控爆设计。','已采用' in h('H_CD6D8392BC7E40A787BD44D82A')['conditions'],'不以推荐装阀文字推出未装即违规；本H仅保留已用阀安装有效性。')
  x=h('H_C9900E360F7848F6AD6025FE89');case('gas_or_dust_not_conjunction',x['id'],'生产过程作业场所仅存在可燃性气体，或仅存在粉尘，而不是二者同时存在。',all('气体或粉尘' in x[f] for f in ['title','description','conditions']) and all('气体和粉尘' not in v for v in x['keywords']),'任一类条件成立即可触发本条防火花要求，不能误改为二者同时存在。')
  x=h('H_AB765CAD382645D0B1024E8CD8');case('fan_material_both_requirements',x['id'],'风机叶片材料已导电，但运行时产生火花。','同时满足导电、运行时不产生火花要求' in x['description'],'不能仅凭已导电排除本条缺陷；两项材料性能均须满足。')
  self.assertEqual(len(cases),16)
  for id,hid,scenario,condition,result in cases:
   with self.subTest(case=id,hazard=hid,scenario=scenario):
    self.assertTrue(condition,result)

if __name__=='__main__':unittest.main()
