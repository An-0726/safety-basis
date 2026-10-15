import fs from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardsDetailed} from '../web/js/search.js';
const row=(id,title,extra={})=>({id,title,searchText:title,aliases:[],keywords:[],lawNames:[],places:[],levels:[],scopes:['全国'],...extra});

test('未安装照明的不同说法不返回灯具损坏，建议能到达有条件的未设置条目',()=>{
  const missing='应设疏散照明的建筑部位未设置疏散照明';
  const broken='已设置的消防应急照明灯具损坏、不能正常点亮';
  const rows=[row('MISSING',missing),row('BROKEN',broken,{searchText:broken+' 应急灯 通道 照明 损坏'})];
  for(const query of ['应急灯没装','应急照明灯未安装','消防应急灯没有安装','通道照明未设置','通道缺少照明','通道未设置照明','通道没装灯']){
    const result=searchHazardsDetailed(rows,query);
    assert.equal(result.rows.length,0,query);
    assert.match(result.queryNotice,/不同缺陷/);
    assert.equal(result.suggestions.length,1);
    assert.deepEqual(searchHazardsDetailed(rows,result.suggestions[0].query).rows.map(r=>r.id),['MISSING']);
  }
  assert.deepEqual(searchHazardsDetailed(rows,broken).rows.map(r=>r.id),['BROKEN']);
  assert.equal(searchHazardsDetailed(rows,'通道没灯').suggestions.length,3);
});

test('缺灯、含糊的化学品存放和油污不被解释成其他缺陷或场所',()=>{
  const rows=[row('SIGN','安全出口或疏散指示标志灯具损坏、不能正常指示',{searchText:'通道 灯 损坏'}),row('DISTANCE','库房物品堆放不符合仓储消防五距及分堆要求',{searchText:'通道 灯'}),row('CHEM','危险化学品仓库未采用规定的储存方式'),row('KITCHEN','餐饮食品处理区地面未保持防滑')];
  for(const query of ['通道没灯','化学品随便放','地上有油']){
    const result=searchHazardsDetailed(rows,query);
    assert.equal(result.rows.length,0);assert.equal(result.matchKind,'none');assert.ok(result.queryNotice);assert.ok(result.suggestions.length>0);
    for(const item of result.suggestions)assert.ok(item.label&&item.query&&item.note);
  }
  assert.equal(searchHazardsDetailed(rows,'车间地上有油').suggestions.length,0);
  assert.equal(searchHazardsDetailed(rows,'普通化学品随便放').suggestions.length,0);
});

test('旋转作业未戴手套不落到佩戴义务；缺防震圈不落到瓶帽',()=>{
  const glove=row('G','生产活动中需使用手部防护装备的作业未正确佩戴',{searchText:'旋转 手套 没戴 佩戴',aliases:['没戴手套'],keywords:['手套']});
  const cap=row('CAP','气瓶未装配保护罩或瓶帽',{searchText:'气瓶 防震圈'});
  assert.equal(searchHazardsDetailed([glove,cap],'旋转作业没戴手套').rows.length,0);
  assert.match(searchHazardsDetailed([glove,cap],'旋转作业没戴手套').queryNotice,/缠绕/);
  assert.equal(searchHazardsDetailed([glove,cap],'气瓶没防震圈').rows.length,0);
  const actual=JSON.parse(fs.readFileSync(new URL('../knowledge/hazards/H_TSG23_CYLINDER_NO_GUARD_OR_CAP.json',import.meta.url),'utf8'));
  assert.ok(![...actual.aliases,...actual.keywords].some(value=>value.includes('防震圈')));
});

test('补录规则按真实标题别名检索，压力表故障与检定严格区分',()=>{
  const source=id=>JSON.parse(fs.readFileSync(new URL(`../knowledge/hazards/${id}.json`,import.meta.url),'utf8'));
  const ids=['H_TSG21_PRESSURE_GAUGE_DAMAGED','H_TSG21_PRESSURE_GAUGE_NOT_VERIFIED','H_GB29512_HAND_PPE_NOT_WORN','H_12158_10_2_1','H_GB12801_STACK_HEIGHT_OR_BASE_UNSAFE'];
  const rows=ids.map(id=>{const h=source(id);return row(id,h.title,{...h,searchText:[h.title,...h.aliases,...h.keywords].join(' ')});});
  assert.deepEqual(searchHazardsDetailed(rows,'压力表坏了').rows.map(r=>r.id),['H_TSG21_PRESSURE_GAUGE_DAMAGED']);
  assert.deepEqual(searchHazardsDetailed(rows,'没戴手套').rows.map(r=>r.id),['H_GB29512_HAND_PPE_NOT_WORN']);
  assert.deepEqual(searchHazardsDetailed(rows,'材料堆太高').rows.map(r=>r.id),['H_GB12801_STACK_HEIGHT_OR_BASE_UNSAFE']);
  assert.equal(searchHazardsDetailed(rows,'压力表坏了',{category:'消防安全'}).rows.length,0);
});
