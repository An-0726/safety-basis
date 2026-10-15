import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardsDetailed,searchLawsDetailed} from '../web/js/search.js';

const row=(id,title,extra={})=>({id,title,searchText:title,aliases:[],keywords:[],lawNames:[],stdNumbers:[],places:[],levels:[],scopes:['全国'],category:'特种设备',status:'已核验',mode:'direct',...extra});
const hook=row('HOOK','起重机吊钩防脱钩装置损坏');
const limiter=row('LIMITER','桥式、门式起重机未按规定安装起升高度限位装置');
const spoken=row('SPOKEN','行车吊钩防脱钩装置损坏');
const bike=row('BIKE','电动自行车飞线充电',{category:'消防安全'});
const braking=row('BRAKE','场内车辆行车制动装置失效');
const exclusion=row('EXCLUSION','移动式压力容器充装违规',{searchText:'移动式压力容器充装违规 排除工地起重机械'});
const rows=[bike,hook,limiter,spoken,braking,exclusion];
const ids=(query,filters={})=>searchHazardsDetailed(rows,query,filters).rows.map(r=>r.id).sort();

test('行车、天车、起重机均检索起重设备，不召回自行车、行车制动或排除范围提及',()=>{
  for(const query of ['行车','天车','起重机'])assert.deepEqual(ids(query),['HOOK','LIMITER','SPOKEN'],query);
});

test('只有自行车或道路车辆时，起重设备别名不制造命中',()=>{
  for(const query of ['行车','天车','起重机','起重机械','起重设备']){
    assert.equal(searchHazardsDetailed([bike,braking,exclusion],query).rows.length,0,query);
  }
});

test('起重机械与起重设备按相关对象检索，保留原词优先的既有规则',()=>{
  for(const query of ['起重机械','起重设备'])assert.deepEqual(ids(query),['HOOK','LIMITER','SPOKEN'],query);
  const dedicated=row('FAMILY','起重设备安全管理缺失');
  assert.deepEqual(searchHazardsDetailed([...rows,dedicated],'起重设备').rows.map(r=>r.id),['FAMILY']);
});

test('行车复合问法有无空格都须同时符合设备和缺陷',()=>{
  for(const query of ['行车 吊钩','行车吊钩','天车吊钩'])assert.deepEqual(ids(query),['HOOK','SPOKEN'],query);
  for(const query of ['行车 限位','行车限位'])assert.deepEqual(ids(query),['LIMITER'],query);
  assert.deepEqual(ids('行车泄漏'),[]);
});

test('口语解释也不能绕过起重对象约束',()=>{
  const result=searchHazardsDetailed(rows,'行车吊钩坏了');
  assert.equal(result.matchKind,'colloquial');
  assert.deepEqual(result.rows.map(r=>r.id).sort(),['HOOK','SPOKEN']);
  assert.equal(searchHazardsDetailed([bike,braking,exclusion],'行车坏了').rows.length,0);
});

test('自行车复合词完整保留，仍可搜索充电及完整标题',()=>{
  for(const query of ['自行车','自行车充电','自行车 充电','电动自行车','电动自行车充电','电动自行车飞线充电'])assert.deepEqual(ids(query),['BIKE'],query);
  assert.equal(searchHazardsDetailed(rows,'自行车充电').interpretedQuery,'自行车 充电');
});

test('明确的起重设备别名或关键词可用，正文顺带提及不能代替对象',()=>{
  const alias=row('ALIAS','施工吊装区域人员管控不到位',{aliases:['起重机周边有无关人员'],searchText:'施工吊装区域人员管控不到位 起重机周边有无关人员'});
  const keyword=row('KEYWORD','设备安全装置故障',{keywords:['起重设备'],searchText:'设备安全装置故障 起重设备'});
  assert.deepEqual(searchHazardsDetailed([alias,keyword,exclusion],'行车').rows.map(r=>r.id),['ALIAS']);
  assert.deepEqual(searchHazardsDetailed([keyword,exclusion],'起重设备').rows.map(r=>r.id),['KEYWORD']);
});

test('修正保留类别筛选及完整标题的精确定位',()=>{
  assert.deepEqual(ids('行车',{category:'消防安全'}),[]);
  assert.deepEqual(ids('行车',{category:'特种设备'}),['HOOK','LIMITER','SPOKEN']);
  assert.deepEqual(ids('场内车辆行车制动装置失效'),['BRAKE']);
});

test('明确查询行车制动或行车道时保留完整词，不按车间起重设备展开',()=>{
  assert.deepEqual(ids('行车制动'),['BRAKE']);
  assert.deepEqual(ids('场内车辆行车制动装置失效'),['BRAKE']);
  const road=row('ROAD','道路行车道被占用');
  assert.deepEqual(searchHazardsDetailed([...rows,road],'行车道').rows.map(r=>r.id),['ROAD']);
});

test('同一段文字提到自行车和起重机时不整条排除，按明确设备字段核对',()=>{
  const mixed=row('MIXED','起重机吊运作业安全措施缺失',{searchText:'起重机吊运作业安全措施缺失 警戒区域不得停放自行车'});
  assert.deepEqual(searchHazardsDetailed([mixed,bike],'行车').rows.map(r=>r.id),['MIXED']);
});

test('法规搜索的同义词不再把自行车管理办法当作起重规程',()=>{
  const laws=['起重机械安全技术规程','南京市电动自行车消防安全管理办法','道路车辆行车制动要求'].map((name,i)=>({id:String(i),name,aliases:[],scope:'全国',status:'现行有效',searchText:name}));
  for(const query of ['行车','天车','起重机','起重机械','起重设备'])assert.deepEqual(searchLawsDetailed(laws,query).rows.map(r=>r.id),['0'],query);
  assert.deepEqual(searchLawsDetailed(laws,'自行车').rows.map(r=>r.id),['1']);
});
