import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {highlightText, zeroResultExplanation, checkedClientVersion} from '../web/app.js';
import {hazardFacetValues, filterHazardFacets, hazardFacetOptions} from '../web/js/search-facets.js';

const row = (title, extra = {}) => ({id:title,title,aliases:[],places:[],...extra});

test('facets distinguish a bicycle from a crane and do not use incidental body or law words', () => {
  const bicycle = row('电动自行车在楼梯间停放', {searchText:'起重机械 灭火器 配电箱 损坏',lawNames:['起重机械标准'],description:'附近配电箱和灭火器正常'});
  assert.deepEqual(hazardFacetValues(bicycle).equipment, ['电动自行车']);
  assert.ok(hazardFacetValues(row('车间行车吊钩损坏')).equipment.includes('起重机械'));
  assert.deepEqual(hazardFacetValues(row('设备检查要求', {description:'起重机损坏',conditions:'适用于仓储物流'})), {
    industry:['未标注行业或场所'],equipment:['其他或未明确设备'],problem:['其他问题'],
  });
});

test('facets keep installation, damage, overdue inspection, missing documents and missing activity separate', () => {
  const missing = hazardFacetValues(row('未安装报警器')).problem;
  const damaged = hazardFacetValues(row('报警器安装后损坏')).problem;
  assert.ok(missing.includes('缺少或未安装'));
  assert.ok(!missing.includes('损坏或失效'));
  assert.ok(damaged.includes('损坏或失效'));
  assert.ok(!damaged.includes('缺少或未安装'));
  const overdue = hazardFacetValues(row('压力表检定超期')).problem;
  assert.ok(overdue.includes('检验检定超期'));
  assert.ok(!overdue.includes('损坏或失效'));
  const docs = hazardFacetValues(row('未提供应急演练记录')).problem;
  const activity = hazardFacetValues(row('未组织应急演练')).problem;
  assert.deepEqual(docs, ['资料记录缺失']);
  assert.deepEqual(activity, ['实际活动未实施']);
  assert.ok(!hazardFacetValues(row('未提供劳动防护用品')).problem.includes('资料记录缺失'));
});

test('industry comes from published places and aliases can supply the item equipment', () => {
  assert.deepEqual(hazardFacetValues(row('设备损坏',{aliases:['灭火器失压'],places:['仓储物流场所']})), {
    industry:['仓储物流'],equipment:['灭火器'],problem:['损坏或失效'],
  });
  assert.deepEqual(hazardFacetValues(row('仓库安全检查')).industry,['未标注行业或场所']);
});

test('facet combinations use AND, keep unknown entries by default, and never mutate rows', () => {
  const rows = [row('灭火器失压',{places:['仓储物流']}),row('灭火器失压',{places:['餐饮厨房']}),row('电箱未接地',{places:['仓储物流']}),row('其他检查')];
  const before = JSON.stringify(rows);
  assert.equal(filterHazardFacets(rows,{}),rows);
  assert.deepEqual(filterHazardFacets(rows,{industry:'仓储物流',equipment:'灭火器',problem:'损坏或失效'}),[rows[0]]);
  assert.deepEqual(filterHazardFacets(rows,{equipment:'未收录设备'}),[]);
  assert.equal(JSON.stringify(rows),before);
});

test('facet options are stable across index order and include unknown values last', () => {
  const rows=[row('电箱未接地'),row('其他检查'),row('灭火器失压',{places:['仓储物流']})];
  const options=hazardFacetOptions(rows);
  assert.deepEqual(options,hazardFacetOptions([...rows].reverse()));
  assert.deepEqual(options.equipment,['灭火器','配电与电气设备','其他或未明确设备']);
  assert.equal(options.industry.at(-1),'未标注行业或场所');
});

test('highlighting is literal, prefers longest phrases and escapes both text and matches', () => {
  assert.equal(highlightText('电箱没有接地，电箱损坏',['电箱','没有接地','接地']),'<mark>电箱</mark><mark>没有接地</mark>，<mark>电箱</mark>损坏');
  assert.equal(highlightText('<img onerror=x> AB[12] &',['<img','AB[12]']),'<mark>&lt;img</mark> onerror=x&gt; <mark>AB[12]</mark> &amp;');
  assert.equal(highlightText('正常内容',['x','.*']),'正常内容');
});

test('zero explanations distinguish no facts, ambiguous query, evidence gap and restrictive filters', () => {
  assert.match(zeroResultExplanation({zeroReason:'fact_unconfirmed'}).title,/尚未确认/);
  assert.match(zeroResultExplanation({zeroReason:'needs_conditions'}).title,/补充/);
  assert.match(zeroResultExplanation({zeroReason:'evidence_gap'}).title,/暂缺/);
  const filtered=zeroResultExplanation({zeroReason:'filters_exclude_matches',unfilteredCount:4},true);
  assert.equal(filtered.clearFilters,true);
  assert.match(filtered.message,/4 条候选/);
  assert.notEqual(zeroResultExplanation({zeroReason:'no_library_match'}).title,filtered.title);
});

test('page/script version checks reject disagreements and allow unresolved development markers', () => {
  assert.equal(checkedClientVersion('2026.11.08','2026.11.08'),'2026.11.08');
  assert.throws(()=>checkedClientVersion('old','new'),error=>error.code==='VERSION_MISMATCH');
  assert.equal(checkedClientVersion('__SAFETY_BASIS_DATA_VERSION__','__SAFETY_BASIS_DATA_VERSION__'),'');
});

test('rendered source still checks real version strings after every build marker is replaced', async () => {
  const sourceUrl=new URL('../web/app.js',import.meta.url);
  const source=fs.readFileSync(sourceUrl,'utf8')
    .replaceAll('__SAFETY_BASIS_DATA_VERSION__','2026.11.08-rendered')
    .replace(/from\s+(['"])(\.\/[^'"]+)\1/g,(_match,quote,path)=>`from ${quote}${new URL(path,sourceUrl).href}${quote}`);
  const rendered=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
  assert.equal(rendered.checkedClientVersion('2026.11.08-rendered','2026.11.08-rendered'),'2026.11.08-rendered');
  assert.throws(()=>rendered.checkedClientVersion('old-page','2026.11.08-rendered'),error=>error.code==='VERSION_MISMATCH');
});

test('communication apparatus has its own equipment facet from titles or aliases', () => {
  for (const name of ['通信装置失效','通讯装置损坏','通信设备无法使用','通讯设备故障']) {
    assert.deepEqual(hazardFacetValues(row(name)).equipment,['通信装置']);
  }
  assert.deepEqual(hazardFacetValues(row('设备失效',{aliases:['通讯装置']})).equipment,['通信装置']);
  assert.deepEqual(hazardFacetValues(row('其他检查',{description:'检查通信设备'})).equipment,['其他或未明确设备']);
});
