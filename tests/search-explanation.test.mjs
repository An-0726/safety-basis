import test from 'node:test';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {searchHazardsDetailed, searchLawsDetailed, searchHazards} from '../web/js/search.js';
import {snapshotNoticeText, canonicalCategoryFilter, parseRoute, routeQuery} from '../web/app.js';

const row=(id,title,extra={})=>({id,title,searchText:title,aliases:[],keywords:[],lawNames:[],places:[],levels:[],scopes:['全国'],category:'电气安全',status:'已核验',mode:'direct',...extra});

test('相关设备回退有明确类型，原词命中时不混入相关设备',()=>{
  const room=row('ROOM','配电室通道堵塞');
  const box=row('BOX','配电箱通道堵塞');
  const related=searchHazardsDetailed([room],'配电箱');
  assert.equal(related.matchKind,'related');assert.deepEqual(related.rows,[room]);
  const exact=searchHazardsDetailed([room,box],'配电箱');
  assert.equal(exact.matchKind,'standard');assert.deepEqual(exact.rows,[box]);
  assert.deepEqual(searchHazards([room,box],'配电箱'),exact.rows);
});

test('纠错只在当前筛选无原词结果后发生，公开解释纠正后的查询',()=>{
  const rows=[row('FIRE','灭火器失压',{category:'消防安全'})];
  assert.equal(searchHazardsDetailed(rows,'灭活器').matchKind,'corrected');
  assert.equal(searchHazardsDetailed(rows,'灭活器').interpretedQuery,'灭火器');
  assert.equal(searchHazardsDetailed(rows,'灭活器',{category:'电气安全'}).matchKind,'none');
  assert.equal(searchHazardsDetailed(rows,'').matchKind,'all');
});

test('无证与持证、干式与湿式、排烟阀与防火阀保持不同含义',()=>{
  for(const [query,title] of [['无证上岗','持证上岗'],['湿式除尘器','干式除尘器'],['排烟阀','防火阀故障']]){
    const result=searchHazardsDetailed([row('NEGATIVE',title)],query);
    assert.equal(result.rows.length,0,query);assert.equal(result.matchKind,'none',query);
  }
});

test('法规同样公开相关概念回退而不改写原始查询',()=>{
  const result=searchLawsDetailed([{id:'L',name:'低压配电设计规范',searchText:'低压配电设计规范',aliases:[],status:'现行有效'}],'配电房规范');
  assert.equal(result.matchKind,'related');assert.equal(result.rows[0].id,'L');
  const route={view:'hazards',query:'灭活器',filters:{scene:'配电室与配电装置'}};
  assert.equal(parseRoute(routeQuery(route)).query,'灭活器');
});

test('快照在中国日期跨日后提示未核验变化，不推断法律失效',()=>{
  assert.equal(snapshotNoticeText('2026-09-30','2026-09-30'),'');
  const warning=snapshotNoticeText('2026-09-30','2026-10-01');
  assert.match(warning,/2026-09-30.*未校验此后的法规变化/);
  assert.doesNotMatch(warning,/已经失效|全部过期|现行有效/);
  assert.match(snapshotNoticeText('2026-10-01','2026-09-30'),/晚于当前日期/);
  assert.match(snapshotNoticeText('未提供','2026-09-30'),/缺少明确快照日期/);
});


test('实际单条别名并入专业分类，旧分类链接只按已投影的唯一目标迁移',()=>{
  const cases=[
    ['H_FORKLIFT_UNATTENDED_KEY','特种设备'],
    ['H_WORKPLACE_CHEM_SDS_MISSING','危险化学品与危险物质'],
    ['H_CF_GEN_18','设备设施'],
  ];
  for(const [id,displayCategory] of cases){
    const source=JSON.parse(fs.readFileSync(new URL(`../knowledge/hazards/${id}.json`,import.meta.url),'utf8'));
    const record=row(id,source.title,{category:source.category,displayCategory});
    assert.equal(canonicalCategoryFilter(source.category,[record]),displayCategory);
    assert.deepEqual(searchHazards([record],'',{category:displayCategory}).map(value=>value.id),[id]);
    assert.equal(searchHazards([record],'',{category:source.category}).length,0);
  }
  for(const id of ['H_PDDB_14_1','H_12158_8_8_5_3','H_CF_GEN_15']){
    const source=JSON.parse(fs.readFileSync(new URL(`../knowledge/hazards/${id}.json`,import.meta.url),'utf8'));
    const record=row(id,source.title,{category:source.category,displayCategory:source.category});
    assert.equal(canonicalCategoryFilter(source.category,[record]),source.category);
  }
});

test('旧分类若对应多个已审核目标，不猜测或扩大为其中一种',()=>{
  const rows=[row('A','气瓶',{category:'设备设施',displayCategory:'特种设备'}),row('B','砂轮',{category:'设备设施',displayCategory:'机械与设备安全'})];
  assert.equal(canonicalCategoryFilter('设备设施',rows),'设备设施');
  assert.equal(canonicalCategoryFilter('未知分类',rows),'未知分类');
});
