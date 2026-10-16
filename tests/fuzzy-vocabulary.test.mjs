import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardsDetailed,searchLawsDetailed} from '../web/js/search.js';

const row=(id,title,extra={})=>({id,title,searchText:title.toLowerCase(),aliases:[],keywords:[],lawNames:[],stdNumbers:[],places:[],levels:[],scopes:['全国'],category:'综合安全',status:'已核验',mode:'direct',...extra});
const ids=(rows,q)=>searchHazardsDetailed(rows,q).rows.map(r=>r.id);
const ppeTitle='作业过程中未按规定正确佩戴和使用劳动防护用品';
const targets=[
  row('PPE',ppeTitle),row('HAND','生产活动中需使用手部防护装备的作业未正确佩戴'),
  row('HAND_RISK','手部防护装备的选用增加缠绕或点火等风险'),
  row('RCD','电动工具回路、检修电源箱未装剩余电流动作保护装置（漏电保护器）或保护装置失效'),
  row('PE','保护接地线连接不可靠或采用缠绕、挂钩'),
  row('STATIC','静电危险场所对地绝缘的设备、管道静电导体未接地'),
  row('EXIT','疏散通道、安全出口或消防车通道被占用、堵塞、封闭'),
  row('HOOK_MISSING','可能导致物品意外脱钩的起重机吊钩未装设防脱钩装置'),
  row('HOOK_DAMAGE','一行车吊钩防脱钩装置损坏'),
  row('GAUGE_CHECK','固定式压力容器压力表未经检定或超过检定有效期'),
  row('VALVE_CHECK','固定式压力容器安全阀超过适用校验周期'),
  row('SE_CHECK','特种设备未按要求办理定期检验'),
  row('TRAINING_RECORD','未建立安全生产教育培训档案并如实记录'),
  row('CAP','气瓶未装配保护罩或瓶帽'),
  row('CYLINDER_STABLE','气瓶放置或立放使用时未采取可靠防倾倒措施'),
  row('HYDRANT_HOSE','室内消火栓箱内未配置消防水带或消防水枪'),
  row('EXT_PRESSURE','灭火器压力指示器的指针,未在绿色范围内'),
  row('SDS','危险化学品使用单位未向从业人员提供安全技术说明书或安全标签'),
  row('TRAINING','从业人员安全教育培训不到位'),
];

test('新增常见俗称通过相同对象检索，组合查询仍要求缺陷命中',()=>{
  for(const [query,title] of [
    ['排插超载','插线板超负荷使用'],['空开','空气开关未标识'],
    ['RCD','剩余电流动作保护器失效'],['护目眼镜检查','防护眼镜未检查'],
    ['冲眼器','洗眼器冲洗空间有障碍物'],['抽风柜','通风柜未设置'],
    ['空压机','空气压缩机未检修'],['龙门吊限位','门式起重机限位故障'],
  ]){
    const good=row('GOOD',title),wrong=row('WRONG','其他设备故障');
    assert.deepEqual(ids([wrong,good],query),['GOOD'],query);
  }
  assert.equal(ids([row('WRONG','门式起重机安全员未培训')],'龙门吊限位').length,0);
});

test('PPE、SDS、RCD、LEL不在英文单词或无关编号内部作子串命中',()=>{
  const noise=row('NOISE','unrelated copper parallel id_asdsx arcdevice');
  for(const q of ['PPE','SDS','RCD','LEL'])assert.equal(ids([noise],q).length,0,q);
  assert.deepEqual(ids([row('SDS','供应商提供MSDS资料')],'SDS'),['SDS']);
  assert.deepEqual(ids([row('RCD','设备配置RCD保护器')],'RCD'),['RCD']);
  assert.deepEqual(ids([row('LEL','检测LEL浓度')],'LEL'),['LEL']);
  const laws=[{id:'NOISE',name:'copper parallel requirements',aliases:[],scope:'全国',status:'现行有效',searchText:noise.searchText}];
  assert.equal(searchLawsDetailed(laws,'LEL').rows.length,0);
  const bodyOnly=row('BODY','asdsx',{searchText:'asdsx sds'});
  const named=row('NAMED','需要SDS资料');
  assert.deepEqual(ids([bodyOnly,named],'SDS'),['NAMED','BODY']);
});

test('天车不匹配露天车间或每天车辆检查，露天车间的原义查询仍可用',()=>{
  const crane=row('CRANE','天车吊钩损坏'),open=row('OPEN','露天车间防火要求'),daily=row('DAILY','每天车辆检查记录');
  assert.deepEqual(ids([open,daily,crane],'天车'),['CRANE']);
  assert.deepEqual(ids([open,crane],'露天车间防火'),['OPEN']);
});

test('进一步选定对象后，正文背景或排除范围提及不代替设备用途',()=>{
  for(const [q,title] of [['压力表','固定式压力容器压力表损坏'],['消防车道','消防车道净空不足'],['危险化学品仓库','危险化学品仓库管理不符合要求'],['火灾自动报警系统','火灾自动报警系统未设置']]){
    const correct=row('CORRECT',title);
    const incidental=row('INCIDENTAL','另一设备安装问题',{searchText:`另一设备安装问题 ${q}`});
    assert.deepEqual(ids([incidental,correct],q),['CORRECT'],q);
  }
});

test('耳塞口罩未佩戴先核岗位需求，不混入安全帽或用品采购责任',()=>{
  const distractors=[row('HELMET','作业人员在应佩戴安全帽的作业场所未佩戴安全帽'),row('PURCHASE','单位未提供符合标准的劳动防护用品')];
  for(const q of ['没戴耳塞','没戴口罩','耳塞没戴','没戴PPE','没戴劳保']){
    const result=searchHazardsDetailed([...targets,...distractors],q);
    assert.equal(result.rows.length,0,q);assert.match(result.queryNotice,/岗位|危害/);
    assert.equal(result.suggestions.length,1,q);
    assert.deepEqual(ids([...targets,...distractors],result.suggestions[0].query),['PPE']);
  }
});

test('手套反向口语保留需求评估及缠绕风险两个分支，不机械要求佩戴',()=>{
  const r=searchHazardsDetailed(targets,'防护手套没戴');
  assert.equal(r.rows.length,0);assert.match(r.queryNotice,/旋转/);
  assert.deepEqual(r.suggestions.flatMap(s=>ids(targets,s.query)),['HAND','HAND_RISK']);
});

test('有条件建议区分对象、缺失损坏、仪表检定和岗位培训记录',()=>{
  for(const [q,expected] of [
    ['地线断了',['PE','STATIC']],['静电线断了',['STATIC']],['PE线断了',['PE']],
    ['漏保失灵',['RCD']],['RCD坏了',['RCD']],
    ['吊钩没保险扣',['HOOK_MISSING']],['吊钩保险坏了',['HOOK_DAMAGE']],
    ['消防通道堵住了',['EXIT']],['逃生门锁住了',['EXIT']],
    ['检定超期',['SE_CHECK','GAUGE_CHECK','VALVE_CHECK']],
    ['培训没签字',['TRAINING_RECORD']],['氧气瓶没帽子',['CAP']],
    ['煤气罐没固定',['CYLINDER_STABLE']],['消防栓水带不见了',['HYDRANT_HOSE']],
    ['灭火器压力低',['EXT_PRESSURE']],['化学品没有MSDS',['SDS']],
    ['新来的没培训',['TRAINING']],['安全培训没做',['TRAINING']],
  ]){
    const r=searchHazardsDetailed(targets,q);
    assert.equal(r.rows.length,0,q);assert.ok(r.queryNotice,q);
    assert.equal(r.interpretedQuery,q,q);
    assert.deepEqual(r.suggestions.flatMap(s=>ids(targets,s.query)),expected,q);
    for(const s of r.suggestions)assert.ok(s.label&&s.query&&s.note,q);
  }
});

test('模糊设备名或操作证必须分清对象，不纠错成另一个设备或资格',()=>{
  const distractors=[row('HYDRANT','消火栓无水'),row('PRESSURE_FAULT','固定式压力容器压力表部件损坏'),row('MAINTENANCE','安全设备维护检测未记录签字')];
  for(const q of ['消防门','气罐','报警器','煤气报警器','四合一','上岗证','操作证','年检']){
    const r=searchHazardsDetailed(distractors,q);
    assert.equal(r.rows.length,0,q);assert.ok(r.queryNotice,q);assert.ok(r.suggestions.length>=2,q);
  }
  assert.match(searchHazardsDetailed(distractors,'动火证').queryNotice,/人员资格/);
});

test('缺证或运行损坏不借未安装、安装位置或未佩戴条目凑结果',()=>{
  for(const q of ['急停失灵','急停按钮按不动','机器护罩坏了','烟感坏掉了','绝缘手套破了','叉车安全带','气瓶圈没了','气瓶减压器','绝缘胶垫']){
    const r=searchHazardsDetailed(targets,q);
    assert.equal(r.rows.length,0,q);assert.equal(r.suggestions.length,0,q);assert.ok(r.queryNotice,q);
  }
});

test('未来到期、未查明、已完成和否定句不被改成已发生的不符合',()=>{
  const future=searchHazardsDetailed(targets,'灭火器快过期');
  assert.equal(future.rows.length,0);assert.match(future.queryNotice,/不等于已经超期/);
  const defects=[row('GROUND_DAMAGE','地线断开'),row('ESTOP_DAMAGE','急停装置失效'),row('TRAINING_UNSIGNED','培训未签字'),row('DOOR_DAMAGE','消防门损坏'),row('REGULATOR_DAMAGE','气瓶减压器损坏')];
  for(const q of ['地线没有断','急停没有失灵','培训已签字','未查明消防门类型','气瓶减压器已修好']){
    const r=searchHazardsDetailed(defects,q);
    assert.equal(r.rows.length,0,q);assert.equal(r.suggestions.length,0,q);
    assert.match(r.queryNotice,/状态词/);
  }
  assert.deepEqual(ids([row('MISSING_BREAKER','配电箱没有断路器')],'配电箱没有断路器'),['MISSING_BREAKER']);
});

test('点击进一步查询保留原筛选，完整规则标题仍可直接定位',()=>{
  const r=searchHazardsDetailed(targets,'培训没签字',{category:'消防安全'});
  assert.equal(r.rows.length,0);
  assert.deepEqual(searchHazardsDetailed(targets,r.suggestions[0].query,{category:'消防安全'}).rows,[]);
  for(const item of targets)assert.deepEqual(ids(targets,item.title),[item.id],item.title);
});
