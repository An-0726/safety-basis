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

test('现场问法不混淆缺少、损坏、安装验收、首次检验和设施种类',()=>{
  const titles={SIGN:'应设灯光疏散指示标志的场所未设置或位置、方向不符合要求',EXTINGUISHER:'应配置灭火器的建筑内未配置灭火器',APPLY:'特种设备未按要求办理定期检验',USE:'特种设备未经定期检验或检验不合格仍继续使用',VENT:'危险化学品储存单位未按种类危险特性设置相应安全设施'};
  const targets=Object.entries(titles).map(([id,title])=>row(id,title));
  const distractors=[
    row('SIGN_FAULT','安全出口或疏散指示标志灯具损坏、不能正常指示',{searchText:'疏散指示 灯 安装 设置'}),
    row('PLACEMENT','灭火器摆放不稳固或铭牌未朝外',{searchText:'灭火器 放 配置'}),
    row('SOCKET','建筑电气安装验收时暗装插座面板或地面插座盖板未固定牢固',{searchText:'插座 损坏'}),
    row('FIRST','场（厂）内专用机动车辆首次投入使用前未完成首次检验',{searchText:'叉车 定期检验 年检'}),
    row('EXPLOSION','经危险区域划分需采用防爆电气的危化品暂存间仍使用非防爆灯具',{searchText:'危化品仓库 通风'}),
  ];
  const rows=[...targets,...distractors];
  const cases=[['疏散指示灯没安装',['SIGN']],['安全出口指示灯没有设置',['SIGN']],['灭火器没放',['EXTINGUISHER']],['仓库没有灭火器',['EXTINGUISHER']],['叉车没有年检',['APPLY','USE']],['叉车定期检验超期',['APPLY','USE']],['危化品仓库没有通风',['VENT']],['危险化学品库房未安装通风设施',['VENT']]];
  for(const [query,ids] of cases){
    const result=searchHazardsDetailed(rows,query);
    assert.equal(result.rows.length,0,query);assert.ok(result.queryNotice,query);
    assert.equal(result.suggestions.length,ids.length,query);assert.equal(result.interpretedQuery,query);
    result.suggestions.forEach((item,i)=>assert.deepEqual(searchHazardsDetailed(rows,item.query).rows.map(r=>r.id),[ids[i]],query));
  }
  const broken=searchHazardsDetailed(rows,'插座坏了');
  assert.equal(broken.rows.length,0);assert.equal(broken.suggestions.length,0);assert.match(broken.queryNotice,/使用期损坏/);
  for(const r of distractors)assert.deepEqual(searchHazardsDetailed([{...r,searchText:r.title+' '+r.searchText}],r.title).rows.map(x=>x.id),[r.id]);
});

test('压力表口语用点击建议确认设备和缺陷，不把指针不动当成未检定',()=>{
  const damage=row('D','固定式压力容器压力表玻璃破裂、刻度不清或部件损坏');
  const verification=row('V','固定式压力容器压力表未经检定或超过检定有效期');
  for(const [query,id] of [['压力表不走了','D'],['压力表玻璃碎了','D'],['压力表检定超期','V']]){
    const result=searchHazardsDetailed([damage,verification],query);
    assert.equal(result.rows.length,0);assert.equal(result.suggestions.length,1);
    assert.deepEqual(searchHazardsDetailed([damage,verification],result.suggestions[0].query).rows.map(r=>r.id),[id]);
    assert.equal(searchHazardsDetailed([damage,verification],result.suggestions[0].query,{category:'消防安全'}).rows.length,0);
  }
});

test('安全出口上锁先区分疏散通行与门禁专用条件',()=>{
  const rows=[row('EXIT','疏散通道、安全出口或消防车通道被占用、堵塞、封闭'),row('GATE','控制人员出入的闸口或门禁疏散出口火灾释放、内部开启或标识不符合要求')];
  for(const query of ['安全出口上锁','安全出口锁了']){
    const result=searchHazardsDetailed(rows,query);
    assert.equal(result.rows.length,0);assert.equal(result.suggestions.length,2);
    result.suggestions.forEach((s,i)=>assert.deepEqual(searchHazardsDetailed(rows,s.query).rows.map(r=>r.id),[['EXIT'],['GATE']][i]));
    assert.match(result.suggestions[1].note,/门禁或闸口/);
  }
});

test('防震胶圈、佩戴和地面问法沿用原有适用性边界',()=>{
  const distractors=[row('CAP','气瓶未装配保护罩或瓶帽',{searchText:'气瓶 钢瓶 防震胶圈'}),row('GLOVE','生产活动中需使用手部防护装备的作业未正确佩戴',{searchText:'钻床 操作 手套 佩戴'}),row('FOOD','餐饮食品处理区地面未保持防滑',{searchText:'车间 地面 油污 湿滑'})];
  for(const query of ['气瓶缺少防震胶圈','钢瓶没有防震胶圈','钻床操作未佩戴手套','旋转作业未佩戴手套','车间地面有油','普通车间地面湿滑']){
    const result=searchHazardsDetailed(distractors,query);assert.equal(result.rows.length,0,query);assert.ok(result.queryNotice,query);
  }
  assert.equal(searchHazardsDetailed(distractors,'车间地面有油').suggestions.length,0);
  assert.equal(searchHazardsDetailed(distractors,'地面有油污').suggestions.length,1);
  assert.equal(searchHazardsDetailed(distractors,'应急照明灯没装过').suggestions.length,1);
});
