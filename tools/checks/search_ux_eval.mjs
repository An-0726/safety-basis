#!/usr/bin/env node
/** Offline, versioned before/after query comparison. The small acceptance file
 * is synthetic and distinct from engine tuning fixtures. It is not a measure
 * of real-world accuracy or a mechanism for declaring a site finding. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash, webcrypto} from 'node:crypto';
import {matchExpectedIssues} from './search_issue_metrics.mjs';

const arg=(name,fallback='')=>{const i=process.argv.indexOf(name);return i<0?fallback:process.argv[i+1];};
const root=path.resolve(arg('--source-root',new URL('../..',import.meta.url).pathname));
const bundle=await fs.realpath(arg('--bundle','source/releases/current'));
const input=await fs.readFile(arg('--cases'),'utf8');
const dataset=JSON.parse(input);
if(!dataset.cases?.length||dataset.cases.some(c=>c.source_kind!=='synthetic'))throw new Error('This public comparison accepts declared synthetic samples only. Use the existing private field-query importer for real samples.');
if(!globalThis.crypto)globalThis.crypto=webcrypto;
const {DataStore}=await import(pathToFileURL(path.join(root,'web/js/store.js')));
const engine=await import(pathToFileURL(path.join(root,'web/js/search.js')));
const fetcher=async url=>{
  const relative=new URL(String(url),'https://bundle.invalid/').pathname.slice(1);
  const target=path.resolve(bundle,relative);
  if(!target.startsWith(bundle+path.sep))throw new Error('Path outside public bundle');
  try{return new Response(await fs.readFile(target),{status:200});}
  catch(error){if(error.code==='ENOENT')return new Response('',{status:404});throw error;}
};
const store=await new DataStore('https://bundle.invalid',{fetcher}).init();
const search=(query,filters)=>engine.searchHazardIssuesDetailed
  ?engine.searchHazardIssuesDetailed(store.searchIndex,query,filters)
  :(()=>{const result=engine.searchHazardsDetailed(store.searchIndex,query,filters);return {...result,isMultiIssue:false,issues:[{...result,query}]};})();
const available=new Set(store.searchIndex.map(row=>row.id));
const results=[];
for(const sample of dataset.cases){
  const allIds=[...(sample.expected_groups||[]).flat(),...(sample.forbidden_ids||[])];
  const unknown=allIds.filter(id=>!available.has(id));
  if(unknown.length)throw new Error(`${sample.id}: labels not in this public release: ${unknown.join(',')}`);
  const result=search(sample.query,sample.filters||{});
  const issues=(result.issues||[result]).map(issue=>({
    query:issue.query||sample.query,interpretedQuery:issue.interpretedQuery||'',
    count:issue.rows?.length||0,top3:(issue.rows||[]).slice(0,3).map(row=>({id:row.id,title:row.title})),
    assessment:issue.assessment||null,notice:issue.queryNotice||'',
    suggestions:(issue.suggestions||[]).map(s=>({query:s.query,label:s.label||s.title||'',top3:engine.searchHazardsDetailed(store.searchIndex,s.query,sample.filters||{}).rows.slice(0,3).map(row=>({id:row.id,title:row.title}))})),
  }));
  const topIds=issues.flatMap(issue=>issue.top3.map(row=>row.id));
  const groupAssignments=matchExpectedIssues(sample.expected_groups||[],issues.map(issue=>issue.top3.map(row=>row.id)));
  const matchedGroups=groupAssignments.map(index=>index>=0);
  const suggestionGroups=(sample.expected_groups||[]).map(ids=>issues.some(issue=>issue.suggestions.some(s=>s.top3.some(row=>ids.includes(row.id)))));
  const forbidden=topIds.filter(id=>(sample.forbidden_ids||[]).includes(id));
  const count=(result.rows||[]).length;
  const assessmentOk=!sample.allowed_assessments||issues.some(issue=>sample.allowed_assessments.includes(issue.assessment?.classification));
  const conditionOk=!sample.required_condition||issues.some(issue=>['needs_conditions','fact_unconfirmed'].includes(issue.assessment?.classification)&&Boolean(issue.notice));
  const filterOk=!sample.expected_filter_empty||count===0&&search(sample.query,{}).rows.length>0;
  const checks={
    direct_top3_hit:matchedGroups.length?matchedGroups.every(Boolean):null,
    suggestion_top3_hit:suggestionGroups.length?suggestionGroups.every(Boolean):null,
    groups_hit:matchedGroups.filter(Boolean).length,expected_groups:matchedGroups.length,group_issue_indices:groupAssignments,
    mismatch:forbidden.length>0||Boolean(sample.empty&&count>0),forbidden_ids:forbidden,
    zero_results:count===0,empty_ok:!sample.empty||count===0,assessment_ok:assessmentOk,condition_ok:conditionOk,
    split_ok:!sample.min_issues||issues.length>=sample.min_issues,
    suggestion_count_ok:!sample.min_suggestions||issues.reduce((n,i)=>n+i.suggestions.length,0)>=sample.min_suggestions,
    filter_explains_empty:filterOk,
  };
  checks.pass=(checks.direct_top3_hit!==false)&&!checks.mismatch&&checks.empty_ok&&assessmentOk&&conditionOk&&checks.split_ok&&checks.suggestion_count_ok&&filterOk;
  results.push({sample,actual:{count,issues},checks});
}
const positive=results.filter(r=>r.checks.direct_top3_hit!==null);
const summary={samples:results.length,synthetic:results.length,real_deidentified:0,
  on_topic_top3:{numerator:positive.filter(r=>r.checks.direct_top3_hit).length,denominator:positive.length},
  targeted_mismatch_samples:results.filter(r=>r.checks.mismatch).length,
  raw_zero_results:results.filter(r=>r.checks.zero_results).length,
  expected_positive_zero_results:positive.filter(r=>r.checks.zero_results).length,
  all_contract_checks:results.filter(r=>r.checks.pass).length,
  limitations:'合成留出样本、助手标注；误匹配仅指已列明禁止目标或否定状态的直接候选，非全库专业准确率。条件建议不合并进原句直接命中率。'};
const implementationFiles={};
for(const name of ['search.js','query-intent.js','search-boundaries.js','search-guidance.js','field-query-guidance.js','search-vocabulary.js']){
  try{implementationFiles[name]=createHash('sha256').update(await fs.readFile(path.join(root,'web/js',name))).digest('hex');}
  catch(error){if(error.code!=='ENOENT')throw error;implementationFiles[name]=null;}
}
const report={schema:'original-site-search-acceptance-report-v1',dataset_sha256:createHash('sha256').update(input).digest('hex'),
  dataVersion:store.manifest.dataVersion,releaseHash:store.manifest.releaseHash,sourceRoot:root,
  implementation_sha256:createHash('sha256').update(await fs.readFile(path.join(root,'web/js/search.js'))).digest('hex'),
  implementation_files:implementationFiles,summary,results};
const out=arg('--out');
if(out){await fs.mkdir(path.dirname(path.resolve(out)),{recursive:true});await fs.writeFile(out,JSON.stringify(report,null,2)+'\n');}
console.log(JSON.stringify(summary,null,2));
for(const r of results.filter(r=>!r.checks.pass))console.log(JSON.stringify({id:r.sample.id,query:r.sample.query,checks:r.checks,top:r.actual.issues.map(i=>i.top3)},null,0));
