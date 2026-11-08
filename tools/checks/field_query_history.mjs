#!/usr/bin/env node
/** Replay the existing published synthetic query report without relabelling it
 * as human truth. Produces an importable pending JSONL and a route comparison. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {REPO_ROOT,validateCases,openPublicStore,evaluateCases,buildReport} from './field_query_eval.mjs';

export function importHistory(history, sourceReference) {
  if (!Array.isArray(history.cases) || !history.cases.length) throw new Error('历史报告缺少 cases');
  return validateCases(history.cases.map((item, i) => ({
    id: `HIST-${String(i + 1).padStart(3, '0')}`, query: item.query,
    source_kind: 'synthetic', annotation_origin: 'historical_regression',
    source_reference: sourceReference, captured_at: history.date,
    deidentified: true, publishable: true, review_status: 'pending',
    expert_label: 'unreviewed', expert_judgment: '历史合成问法回放；旧搜索输出仅作行为对照，尚未经新的独立专业判读。',
    group: item.group || 'historical', required_facts: [], filters: {},
  })));
}

export function compareHistory(history, results, availableIds) {
  return results.map((result, index) => {
    const before = history.cases[index].after;
    const after = result.actual;
    const oldTop3 = (before.ids || []).slice(0, 3);
    const oldSuggestionQueries = (before.suggestions || []).map(s => s.query);
    const newSuggestionQueries = after.suggestions.map(s => s.query);
    const unavailableHistoricalIds = [...new Set([...(before.ids || []), ...(before.suggestions || []).flatMap(s => s.ids || [])])].filter(id => !availableIds.has(id));
    const nowIds = after.top3.map(r => r.hazard_id);
    const same = before.count === after.result_count
      && JSON.stringify(oldTop3) === JSON.stringify(nowIds)
      && Boolean(before.notice) === Boolean(after.notice)
      && JSON.stringify(oldSuggestionQueries) === JSON.stringify(newSuggestionQueries);
    return {id: result.sample.id, query: result.sample.query, group: result.sample.group,
      unchanged_route_and_top3: same, unavailable_historical_ids: unavailableHistoricalIds,
      before: {result_count: before.count, top3_hazard_ids: oldTop3, notice: before.notice, suggestion_queries: oldSuggestionQueries},
      after: {result_count: after.result_count, top3_hazard_ids: nowIds, notice: after.notice, outcome: after.outcome, suggestion_queries: newSuggestionQueries}};
  });
}

export async function main(argv=process.argv.slice(2)) {
  const options={};
  for(let i=0;i<argv.length;i++) {
    if(argv[i]==='--help') {console.log('node tools/checks/field_query_history.mjs --bundle source/releases/current [--history docs/FUZZY_QUERY_CHECK_20261016.json] [--output private-intake/search-evaluation/history-120]');return;}
    if(!['--bundle','--history','--output'].includes(argv[i])||!argv[i+1]||argv[i+1].startsWith('--')) throw new Error('参数无效；使用 --help');
    options[argv[i].slice(2)]=argv[++i];
  }
  if(!options.bundle) throw new Error('必须指定 --bundle');
  const source=path.resolve(options.history||path.join(REPO_ROOT,'docs/FUZZY_QUERY_CHECK_20261016.json'));
  const bytes=await fs.readFile(source);
  const history=JSON.parse(bytes.toString('utf8'));
  const cases=importHistory(history,path.relative(REPO_ROOT,source));
  const output=path.resolve(options.output||path.join(REPO_ROOT,'private-intake/search-evaluation/history-120'));
  const opened=await openPublicStore(options.bundle);
  let report,comparison;
  try {
    const results=await evaluateCases(cases,opened.store);
    report=buildReport(results,{history_sha256:createHash('sha256').update(bytes).digest('hex'),history_date:history.date,
      data_manifest:opened.store.manifest,public_hazard_count:opened.store.searchIndex.length,
      interpretation:'历史合成输出作兼容性对照，不是人工判读，不计准确率。'});
    const rows=compareHistory(history,results,new Set(opened.store.searchIndex.map(r=>r.id)));
    comparison={samples:rows.length,unchanged_route_and_top3:rows.filter(r=>r.unchanged_route_and_top3).length,
      changed_route_and_top3:rows.filter(r=>!r.unchanged_route_and_top3).length,
      unavailable_historical_id_samples:rows.filter(r=>r.unavailable_historical_ids.length).length,
      current_outcomes:results.reduce((out,r)=>{out[r.actual.outcome]=(out[r.actual.outcome]||0)+1;return out;},{}),
      real_samples:0,human_reviewed_real_samples:0,rows};
  } finally {await opened.close();}
  await fs.mkdir(output,{recursive:true,mode:0o700});
  await fs.writeFile(path.join(output,'import-pending.jsonl'),cases.map(c=>JSON.stringify(c)).join('\n')+'\n',{mode:0o600});
  await fs.writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n',{mode:0o600});
  await fs.writeFile(path.join(output,'comparison.json'),JSON.stringify(comparison,null,2)+'\n',{mode:0o600});
  const {rows,...summary}=comparison;
  console.log(JSON.stringify({...summary,report_directory:output},null,2));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href) main().catch(error=>{console.error(`历史回放未完成：${error.message}`);process.exitCode=2;});
