import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardsDetailed} from '../web/js/search.js';
const row=(id,title,extra={})=>({id,title,searchText:title,aliases:[],keywords:[],lawNames:[],places:[],levels:[],scopes:['全国'],...extra});
const ids=r=>r.rows.map(x=>x.id);

test('检定状态不能从损坏规则的排除性说明里取得正向命中',()=>{
  const verified=row('H_VERIFIED','固定式压力容器压力表未经检定或超过检定有效期',{searchText:'固定式压力容器 压力表 未经检定 检定超期 检定有效期 损坏另核',category:'特种设备'});
  const damaged=row('H_DAMAGED','固定式压力容器压力表玻璃破裂、刻度不清或部件损坏',{searchText:'固定式压力容器 压力表 损坏 检定超期另核 检定过期 不用于检定状态',category:'特种设备'});
  for(const q of ['固定式压力容器压力表检定超期','固定式压力容器压力表检定过期']){
    const result=searchHazardsDetailed([damaged,verified],q);
    assert.deepEqual(ids(result),['H_VERIFIED'],q);assert.equal(result.assessment.classification,'needs_conditions');
    assert.ok(result.assessment.requiredFacts.some(f=>f.includes('有效期')));
  }
  assert.deepEqual(ids(searchHazardsDetailed([verified,damaged],'固定式压力容器压力表损坏')),['H_DAMAGED']);
  assert.deepEqual(ids(searchHazardsDetailed([verified,damaged],verified.title)),['H_VERIFIED']);
  assert.deepEqual(ids(searchHazardsDetailed([verified,damaged],'固定式压力容器压力表检定超期',{category:'消防安全'})),[]);
});

test('增加场所前缀的未配置问法仍与灯具损坏及指示标志分开',()=>{
  const title='应设疏散照明的建筑部位未设置疏散照明';
  const rows=[row('H_MISSING',title),row('H_SIGN','应设灯光疏散指示标志的场所未设置',{searchText:'车间 应急灯 没有安装'}),row('H_BROKEN','已设置的消防应急照明灯具损坏、不能正常点亮')];
  for(const q of ['车间应急灯没有安装','仓库内应急照明灯未设置','现场应急灯缺失']){
    const result=searchHazardsDetailed(rows,q);assert.deepEqual(ids(result),[],q);assert.equal(result.assessment.classification,'needs_conditions');
    assert.deepEqual(ids(searchHazardsDetailed(rows,result.suggestions[0].query)),['H_MISSING']);
  }
  assert.deepEqual(ids(searchHazardsDetailed(rows,rows[2].title)),['H_BROKEN']);
});

test('缺防震圈是缺证提示，不能命中瓶帽保护罩',()=>{
  const cap=row('H_CAP','气瓶未装配保护罩或瓶帽',{searchText:'气瓶 防震圈 丢失 缺少'});
  for(const q of ['气瓶防震圈丢失','钢瓶缺少防震胶圈']){
    const result=searchHazardsDetailed([cap],q);assert.deepEqual(ids(result),[]);assert.equal(result.assessment.classification,'evidence_gap');assert.equal(result.suggestions.length,0);
  }
  assert.deepEqual(ids(searchHazardsDetailed([cap],cap.title)),['H_CAP']);
});

test('消防门未辨识时不返回消火栓箱门，明确消火栓对象仍可检索',()=>{
  const hydrant=row('H_HYDRANT','消火栓被遮挡、圈占',{searchText:'消火栓 消防门 车间 关不上'});
  const result=searchHazardsDetailed([hydrant],'车间消防门关不上');
  assert.deepEqual(ids(result),[]);assert.equal(result.assessment.classification,'needs_conditions');assert.match(result.queryNotice,/不能解释成消火栓箱门/);
  assert.deepEqual(ids(searchHazardsDetailed([hydrant],hydrant.title)),['H_HYDRANT']);
});

test('行车与自行车对象隔离继续生效',()=>{
  const crane=row('H_CRANE','一行车吊钩防脱钩装置损坏');
  const bike=row('H_BIKE','电动自行车飞线充电',{searchText:'电动自行车 行车吊钩防脱钩装置损坏 仅为无关的排除说明'});
  assert.deepEqual(ids(searchHazardsDetailed([bike,crane],'行车吊钩防脱钩装置损坏')),['H_CRANE']);
  assert.deepEqual(ids(searchHazardsDetailed([bike,crane],bike.title)),['H_BIKE']);
});

test('普通化学品未分类不能补造危化品身份和仓库场景',()=>{
  const hazardous=row('H_CHEM','危险化学品仓库未采用规定的储存方式',{searchText:'普通化学品 未分类存放 混放 危险化学品'});
  const result=searchHazardsDetailed([hazardous],'普通化学品未分类存放');
  assert.deepEqual(ids(result),[]);assert.equal(result.assessment.classification,'needs_conditions');assert.equal(result.suggestions.length,0);
  assert.ok(result.assessment.requiredFacts.some(f=>/物料.*危险/.test(f)));
  assert.deepEqual(ids(searchHazardsDetailed([hazardous],hazardous.title)),['H_CHEM']);
});

test('资料未提供不能转成未实施、超期或设备故障',()=>{
  const target='未建立安全生产教育培训档案并如实记录';
  const rows=[row('H_DOCUMENT',target),row('H_UNTRAINED','生产经营单位未培训从业人员或未合格即上岗',{searchText:'培训签到表 缺签字'}),row('H_FAULT','设备故障',{searchText:'没有找到设备检验报告'})];
  const record=searchHazardsDetailed(rows,'培训签到表缺签字');assert.deepEqual(ids(record),[]);assert.match(record.queryNotice,/不能由缺签字推定未培训/);
  assert.deepEqual(ids(searchHazardsDetailed(rows,record.suggestions[0].query)),['H_DOCUMENT']);
  for(const q of ['没有找到设备检验报告','资料核查：年度消防检测报告缺失']){
    const result=searchHazardsDetailed(rows,q);assert.deepEqual(ids(result),[]);assert.equal(result.assessment.classification,'needs_conditions');assert.ok(result.assessment.requiredFacts.length);
  }
  assert.deepEqual(ids(searchHazardsDetailed(rows,rows[1].title)),['H_UNTRAINED']);
});

test('未发现、未确认与已修复保持事实状态，缺证分型不靠查询前缀猜测',()=>{
  for(const q of ['现场未发现灭火器损坏','车间灯具已经修复','尚未确认安全出口是否堵塞','气瓶防震圈没有损坏','培训记录已经签字']){
    const result=searchHazardsDetailed([],q);assert.equal(result.assessment.classification,'fact_unconfirmed',q);assert.deepEqual(ids(result),[]);
  }
  assert.equal(searchHazardsDetailed([],'插座坏了').assessment.classification,'evidence_gap');
  assert.equal(searchHazardsDetailed([],'普通工业车间地面有油').assessment.classification,'evidence_gap');
  assert.equal(searchHazardsDetailed([],'地面有油').assessment.classification,'needs_conditions');
});

// These existing guards already said the dedicated source is missing; preserve
// that distinction in the newly exposed structured disposition as well.
test('既有缺证提示与机器分类一致，不把无可用专用依据改成确定命中',()=>{
  for(const query of ['绝缘胶垫','气瓶减压器','气瓶圈没了','叉车安全带','绝缘手套破了']) {
    const result=searchHazardsDetailed([],query);
    assert.equal(result.assessment.classification,'evidence_gap',query);
    assert.equal(result.rows.length,0,query);
    assert.ok(result.queryNotice,query);
  }
});


test('灭火器前堆放纸箱保留观察并提示核实取用，不推定障碍',()=>{
  const title='灭火器被遮挡、取用受阻';
  const rows=[row('H_EXT',title),row('H_HYDRANT','消火栓被遮挡、圈占',{searchText:'灭火器前堆放纸箱'})];
  for(const query of ['灭火器前堆放纸箱','车间灭火器前面堆有杂物']) {
    const result=searchHazardsDetailed(rows,query);
    assert.deepEqual(ids(result),[]);
    assert.equal(result.assessment.classification,'needs_conditions');
    assert.equal(result.assessment.reason,'extinguisher_access_observation');
    assert.ok(result.assessment.requiredFacts.some(f=>f.includes('取用')));
    assert.deepEqual(ids(searchHazardsDetailed(rows,result.suggestions[0].query)),['H_EXT']);
  }
  assert.deepEqual(ids(searchHazardsDetailed(rows,title)),['H_EXT']);
});
