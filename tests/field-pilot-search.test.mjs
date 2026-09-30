import test from 'node:test';
import assert from 'node:assert/strict';
import {searchPilot} from '../web/js/field-pilot-search.js';

// Synthetic software fixtures only; no field observation or legal approval.
function row(id, title, extra={}) {
  return {id, title, description:title, searchText:title, aliases:[], keywords:[],
    lawNames:[], status:'本地候选', mode:'conditional', places:[], levels:[], scopes:['CN'],
    inspectionClass:'core_onsite_inspection', defaultFieldEntry:'conditional',
    caseRole:'positive', ...extra};
}
const rows = [
  row('SYN_BOUNDARY','可燃气体报警条件未知',{caseRole:'counterexample'}),
  row('SYN_GAS','可燃气体报警装置故障'),
  row('SYN_EX','防爆电气外壳损坏'),
  row('SYN_FIRE','灭火器损坏'),
  row('SYN_EXCLUDED','可燃气体报警资料',{defaultFieldEntry:'exclude'}),
  row('SYN_UNKNOWN','可燃气体报警待定',{defaultFieldEntry:'undetermined'}),
  row('SYN_DOC','评价报告',{inspectionClass:'document_review',defaultFieldEntry:'exclude'}),
  row('SYN_SPECIAL','社会风险',{inspectionClass:'special_review'}),
  row('SYN_LAW','宣传义务',{inspectionClass:'legal_obligation'}),
  row('SYN_UNDECIDED','对象未知',{inspectionClass:'undetermined'})
];
test('synthetic queries find distinct equipment families',()=>{
  for(const [q,id] of [['可燃气体报警','SYN_GAS'],['防爆电气','SYN_EX'],['灭火器','SYN_FIRE']])
    assert.equal(searchPilot(rows,q)[0].id,id);
  for(const q of ['防静电接地','应急照明','洗眼器'])assert.equal(searchPilot(rows,q).length,0);
  assert.equal(searchPilot(rows,'防爆电器')[0].id,'SYN_EX');
});
test('default route retains conditional boundaries and excludes other purposes',()=>{
  assert.deepEqual(new Set(searchPilot(rows).map(x=>x.id)),new Set(['SYN_GAS','SYN_EX','SYN_FIRE','SYN_BOUNDARY']));
  for(const [q,scope,id] of [['评价报告','document_review','SYN_DOC'],['社会风险','special_review','SYN_SPECIAL'],['宣传','legal_obligation','SYN_LAW'],['对象未知','undetermined','SYN_UNDECIDED']])
    assert.equal(searchPilot(rows,q,scope)[0].id,id);
});
test('explicit boundary queries preserve relevance and inputs stay unchanged',()=>{
  const before=structuredClone(rows);
  assert.equal(searchPilot(rows,'条件未知')[0].id,'SYN_BOUNDARY');
  assert.deepEqual(searchPilot([], '灭火器'),[]);
  assert.deepEqual(rows,before);
});
