import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {parseCsv,validateCases,readDataset,evaluateCases,buildReport,renderMarkdown,assertSafeOutput,checkReport,REPO_ROOT} from '../tools/checks/field_query_eval.mjs';
import {importHistory,compareHistory} from '../tools/checks/field_query_history.mjs';
const sample=(extra={})=>({id:'S1',query:'气瓶未装配保护罩或瓶帽',source_kind:'synthetic',annotation_origin:'assistant_synthetic',review_status:'reviewed',expected_outcome:'candidate_matches',expert_label:'direct_correct',expert_judgment:'合成检索边界样本，仍须核实事实。',publishable:true,...extra});
const row=(id,title,extra={})=>({id,title,searchText:title,aliases:[],keywords:[],lawNames:[],places:[],levels:[],scopes:['全国'],...extra});
const rows=[row('H_CAP','气瓶未装配保护罩或瓶帽'),row('H_OTHER','电动自行车飞线充电'),row('H_MISSING','应设疏散照明的建筑部位未设置疏散照明')];
const store={searchIndex:rows,async getHazardDetail(row){return {hazard:row,bases:[{ref:{linkId:row.id==='H_CAP'?'K_CAP':row.id==='H_OTHER'?'K_OTHER':'K_MISSING',applicability:'适用性须审核'},clause:{id:'C_TEST'},law:{id:'LV_TEST'},sourceUrl:'https://www.gov.cn/'}]};}};
const evaluate=async records=>buildReport(await evaluateCases(validateCases(records),store));

// Parser tests exercise actual spreadsheet exports: quoted commas, newlines,
// CRLF, UTF-8 BOM, escaped quotes, and JSON cells without altering original wording.
test('CSV 原问法保留逗号、双引号、换行及边缘空白，布尔和 JSON 单元格保持类型',()=>{
  const result=parseCsv('\uFEFFid,query,deidentified,required_facts\r\nS1,"  检查,\"\"原话\"\"\n待核  ",true,"[{""fact"":""类型"",""status"":""unconfirmed""}]"\r\n');
  assert.equal(result[0].query,'  检查,"原话"\n待核  ');assert.equal(result[0].deidentified,true);assert.equal(result[0].required_facts[0].status,'unconfirmed');
  assert.throws(()=>parseCsv('id,query\nS1,"未闭合'),/引号未闭合/);
  assert.throws(()=>parseCsv('id,query\nS1,"x"junk'),/结束引号/);
  assert.throws(()=>parseCsv('id,id\nS1,S1'),/重复/);
  assert.throws(()=>parseCsv('id,query\nS1,x,extra'),/列数/);
});

test('导入拒绝未脱敏真记录、重复ID、未知字段和伪复核，绝不自动确认事实',()=>{
  assert.throws(()=>validateCases([sample({source_kind:'real_deidentified',annotation_origin:'human'})]),/脱敏/);
  assert.throws(()=>validateCases([sample(),sample()]),/唯一/);
  assert.throws(()=>validateCases([sample({unknown:'private'})]),/不支持/);
  assert.throws(()=>validateCases([sample({expert_label:'unreviewed'})]),/已复核/);
  assert.throws(()=>validateCases([sample({expected_outcome:undefined})]),/至少有期望分类/);
  const r=validateCases([sample({required_facts:[{fact:'设备类型',status:'unconfirmed',evidence:'待补'}]})]);
  assert.equal(r[0].required_facts[0].status,'unconfirmed');
});

test('JSONL导入保留原问法和标注，报错不输出私有原句',async()=>{
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'field-eval-test-'));
  try{
    const file=path.join(directory,'query.jsonl');const record=sample({query:'  原始问法\n第二行  '});
    await fs.writeFile(file,JSON.stringify(record)+'\n');const data=await readDataset(file);
    assert.equal(data.cases[0].query,record.query);assert.match(data.inputSha256,/^[a-f0-9]{64}$/);
    await fs.writeFile(file,'{"query":"PRIVATE_COMPANY_SECRET"\n');
    await assert.rejects(readDataset(file),e=>!e.message.includes('PRIVATE_COMPANY_SECRET')&&e.message.includes('无法解析'));
  }finally{await fs.rm(directory,{recursive:true,force:true});}
});

test('H和K必须在同一候选中命中；未发布期望编号单独报告且验收失败',async()=>{
  const good=await evaluate([sample({expected_hazard_ids:['H_CAP'],expected_basis_ids:['K_CAP']})]);
  assert.equal(good.summary.direct_top3.rate,1);assert.equal(checkReport(good),true);
  const unrelated=await evaluate([sample({expected_hazard_ids:['H_CAP'],expected_basis_ids:['K_OTHER']})]);
  assert.equal(unrelated.summary.direct_top3.rate,0);assert.equal(checkReport(unrelated),false);
  const missing=await evaluate([sample({expected_hazard_ids:['H_NOT_PUBLISHED']})]);
  assert.deepEqual(missing.results[0].checks.unavailable_expected_ids,['H_NOT_PUBLISHED']);assert.equal(missing.summary.direct_top3.rate,null);assert.equal(checkReport(missing),false);
});

test('条件建议单独计分，不提升原问法Top3，也不跳过原有筛选条件',async()=>{
  const condition=sample({query:'车间应急灯没有安装',expert_label:'needs_conditions',expected_outcome:'needs_conditions',expected_target_route:'suggestion',expected_hazard_ids:['H_MISSING']});
  const report=await evaluate([condition]);
  assert.equal(report.results[0].actual.top3.length,0);assert.equal(report.summary.direct_top3.denominator,0);assert.equal(report.summary.conditional_suggestion_top3.rate,1);assert.equal(checkReport(report),true);
  const filtered=await evaluate([{...condition,filters:{category:'NOT_APPLICABLE'}}]);
  assert.equal(filtered.results[0].actual.suggestions[0].top3.length,0);assert.equal(checkReport(filtered),false);
  const either=await evaluate([{...condition,expected_target_route:'either'}]);
  assert.equal(either.summary.either_route_top3.rate,1);assert.equal(either.summary.direct_top3.denominator,0);assert.equal(checkReport(either),true);
});

test('严重误匹配按人工禁止H/K计数，原结果和建议均检查',async()=>{
  const report=await evaluate([sample({forbidden_basis_ids:['K_CAP'],forbidden_match_kind:'object_mismatch'})]);
  assert.equal(report.summary.severe_mismatch_top3.rate,1);assert.equal(checkReport(report),false);
  const suggestion=await evaluate([sample({query:'车间应急灯没有安装',expert_label:'needs_conditions',forbidden_hazard_ids:['H_MISSING']})]);
  assert.equal(suggestion.summary.severe_mismatch_top3.rate,0);assert.equal(suggestion.summary.forbidden_suggestion_samples,1);assert.equal(checkReport(suggestion),false);
  const missing=await evaluate([sample({forbidden_hazard_ids:['H_NOT_PUBLISHED'],forbidden_basis_ids:['K_NOT_PUBLISHED']})]);
  assert.deepEqual(missing.results[0].checks.unavailable_forbidden_ids,['H_NOT_PUBLISHED','K_NOT_PUBLISHED']);assert.equal(missing.summary.severe_mismatch_top3.rate,null);assert.equal(checkReport(missing),false);
});

test('无真实样本和未复核样本不制造准确率；仅合成通过不代表真人验收',async()=>{
  const report=await evaluate([sample({expected_hazard_ids:['H_CAP']}),sample({id:'P1',review_status:'pending',expert_label:'unreviewed',expected_hazard_ids:['H_OTHER']})]);
  assert.equal(report.real_sample_count,0);assert.equal(report.human_reviewed_real.direct_top3.rate,null);assert.equal(report.summary.direct_top3.denominator,1);assert.equal(report.summary.pending,1);
  const pending=await evaluate([sample({review_status:'pending',expert_label:'unreviewed'})]);assert.equal(checkReport(pending),false);
  const real=await evaluate([sample({source_kind:'real_deidentified',annotation_origin:'human',deidentified:true,expected_hazard_ids:['H_CAP']})]);
  assert.equal(real.human_reviewed_real_sample_count,1);assert.equal(real.human_reviewed_real.direct_top3.denominator,1);
});

test('私有报告拒绝公开目录和绕过忽略目录的符号链接',async()=>{
  const cases=validateCases([sample({source_kind:'real_deidentified',annotation_origin:'human',deidentified:true})]);
  await assert.rejects(assertSafeOutput(path.join(REPO_ROOT,'docs/private-results'),cases),/private-intake/);
  const privateRoot=path.join(REPO_ROOT,'private-intake');await fs.mkdir(privateRoot,{recursive:true});
  const directory=await fs.mkdtemp(path.join(privateRoot,'eval-test-'));
  try{
    assert.equal(await assertSafeOutput(path.join(directory,'reports'),cases),path.join(directory,'reports'));
    await fs.symlink(path.join(REPO_ROOT,'docs'),path.join(directory,'public-link'));
    await assert.rejects(assertSafeOutput(path.join(directory,'public-link','leak'),cases),/private-intake/);
  }finally{await fs.rm(directory,{recursive:true,force:true});}
});

test('Markdown报告转义原句中的HTML及表格符号，JSON仍保留原始问法',async()=>{
  const query='<script>alert(1)</script>|原句';const report=await evaluate([sample({query})]);
  const markdown=renderMarkdown(report);assert.ok(!markdown.includes('<script>'));assert.ok(markdown.includes('&lt;script&gt;'));assert.equal(report.results[0].sample.query,query);
});


test('历史语料导入保留原问法且不把旧检索输出冒充人工期望',async()=>{
  const history={date:'2026-10-16',cases:[{group:'historical',query:'气瓶未装配保护罩或瓶帽',after:{count:1,ids:['H_CAP'],notice:'',suggestions:[]}}]};
  const records=importHistory(history,'docs/history.json');
  assert.equal(records[0].query,history.cases[0].query);
  assert.equal(records[0].review_status,'pending');assert.equal(records[0].annotation_origin,'historical_regression');
  assert.deepEqual(records[0].expected_hazard_ids,[]);assert.equal(records[0].expert_label,'unreviewed');
  const results=await evaluateCases(records,store);const report=buildReport(results);
  assert.equal(report.summary.reviewed,0);assert.equal(report.summary.direct_top3.rate,null);
  assert.equal(report.real_sample_count,0);assert.equal(checkReport(report),false);
  const comparison=compareHistory(history,results,new Set(rows.map(r=>r.id)));
  assert.equal(comparison[0].unchanged_route_and_top3,true);
  history.cases[0].after.ids=['H_NO_LONGER_PUBLISHED'];
  const changed=compareHistory(history,results,new Set(rows.map(r=>r.id)));
  assert.equal(changed[0].unchanged_route_and_top3,false);assert.deepEqual(changed[0].unavailable_historical_ids,['H_NO_LONGER_PUBLISHED']);
});
