import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {searchPilot} from '../web/js/field-pilot-search.js';

const rows=fs.readdirSync(new URL('../knowledge/field-profiles-pilot/records/',import.meta.url)).map(file=>{
  const p=JSON.parse(fs.readFileSync(new URL(`../knowledge/field-profiles-pilot/records/${file}`,import.meta.url),'utf8'));
  return {...p,aliases:p.searchTerms||[],keywords:[p.object,p.defect],lawNames:[],status:'本地候选',mode:'conditional',places:[],levels:[],scopes:['CN'],searchText:[p.id,p.hazardId,p.title,p.object,p.defect,p.findingTemplate,...(p.searchTerms||[])].filter(Boolean).join(' ')};
});
test('three user queries find concrete defect families',()=>{
  for(const [query,expected] of [['可燃气体报警',['FP_P01','FP_P02','FP_P03','FP_P04','FP_P05']],['防爆电气',['FP_P06','FP_P07','FP_P08','FP_P09']],['灭火器',['FP_P10','FP_P11','FP_P12','FP_P13','FP_P14','FP_P15']]]){
    const ids=searchPilot(rows,query).map(x=>x.id);expected.forEach(id=>assert.ok(ids.includes(id),`${query} missing ${id}`));
    assert.equal(searchPilot(rows,query)[0].caseRole,'positive');
  }
});
test('default field route excludes screenshots/media and keeps conditional boundaries',()=>{
  const ids=searchPilot(rows).map(x=>x.id);
  for(const id of ['FP_N01','FP_N02','FP_N03','FP_N05'])assert.ok(!ids.includes(id));
  for(const id of ['FP_N04','FP_N06'])assert.ok(ids.includes(id));
  assert.equal(searchPilot(rows,'社会风险','special_review')[0].id,'FP_N01');
  assert.equal(searchPilot(rows,'评价报告','document_review')[0].id,'FP_N02');
  assert.equal(searchPilot(rows,'宣传','legal_obligation')[0].id,'FP_N03');
});
test('unconfirmed quantity and area do not carry a violation template',()=>{
  for(const id of ['FP_N04','FP_N05','FP_N06'])assert.equal(rows.find(x=>x.id===id).findingTemplate,null);
});
test('equipment concepts do not replace one another',()=>{
  assert.equal(searchPilot(rows,'防静电接地').length,0);
  assert.equal(searchPilot(rows,'应急照明').length,0);
  assert.equal(searchPilot(rows,'洗眼器').length,0);
  assert.ok(searchPilot(rows,'防爆电器').some(x=>x.id==='FP_P06'));
});
