import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardsDetailed} from '../web/js/search.js';

const row=(id,title,extra={})=>({id,title,searchText:title.toLowerCase(),aliases:[],keywords:[],lawNames:[],places:[],levels:[],scopes:['全国'],category:'综合安全',status:'已核验',mode:'direct',...extra});
// 标题取自已发布条目，口语问法取自现场检查常用说法。
const rows=[
  row('EXT_SCRAP','灭火器未按要求维护、维修或报废更换'),
  row('EXT_BLOCK','灭火器被遮挡、取用受阻'),
  row('HYDRANT','消火栓被遮挡、圈占'),
  row('BOX_PE','装有电器的可开启配电箱（柜）门与金属框架未可靠连接',{searchText:'装有电器的可开启配电箱 柜 门与金属框架未可靠连接 保护接地'}),
  row('BOX_FRONT','配电箱（柜）前堆放杂物，操作通道或维护空间被遮挡、占用'),
  row('CYL','气瓶放置或立放使用时未采取可靠防倾倒措施'),
  row('EXIT','疏散通道、安全出口或消防车通道被占用、堵塞、封闭'),
  row('SIGN','安全出口或疏散指示标志灯具损坏、不能正常指示'),
  row('VALVE','固定式压力容器安全阀超过适用校验周期'),
  row('WHEEL','手持砂轮机防护罩缺失。'),
  row('BELT','传动带、明齿轮、联轴器、皮带轮未设置防护罩'),
  row('DRILL','生产经营单位未制定本单位应急预案演练计划',{searchText:'生产经营单位未制定本单位应急预案演练计划 应急演练'}),
  row('LICENSED','特种作业人员持证上岗'),
  row('DRY','干式除尘器泄爆口朝向不符合要求'),
];
const top=query=>searchHazardsDetailed(rows,query);

test('口语问法落到对应条目，并公开实际使用的查找词',()=>{
  for(const [query,id] of [
    ['灭火器过期','EXT_SCRAP'],['灭火器过期了','EXT_SCRAP'],['灭火器被挡住','EXT_BLOCK'],['消防栓被东西挡住了','HYDRANT'],
    ['配电箱没接地','BOX_PE'],['配电箱前堆东西','BOX_FRONT'],['气瓶没固定','CYL'],['通道堵了','EXIT'],
    ['安全出口锁了','EXIT'],['疏散指示坏了','SIGN'],['安全阀过期','VALVE'],['砂轮机没防护罩','WHEEL'],
    ['皮带没护罩','BELT'],['没做应急演练','DRILL'],['除尘器没泄爆','DRY'],
  ]){
    const result=top(query);
    assert.equal(result.matchKind,'colloquial',query);
    assert.equal(result.rows[0]?.id,id,query);
    assert.ok(result.interpretedQuery&&!/没|了|被/.test(result.interpretedQuery),query);
  }
});

test('原词能命中时不启用口语解释',()=>{
  const result=top('灭火器 遮挡');
  assert.equal(result.matchKind,'standard');assert.deepEqual(result.rows.map(r=>r.id),['EXT_BLOCK']);
});

test('口语解释不做部分匹配：对象或缺陷对不上就不返回',()=>{
  for(const query of ['没戴安全帽','楼梯没扶手','叉车没证','湿式除尘器没泄爆','氧气乙炔放一起','配电箱没泄爆']){
    const result=top(query);
    assert.equal(result.rows.length,0,query);assert.equal(result.matchKind,'none',query);
  }
  // “没证”不能落到“持证上岗”。
  assert.equal(top('电工没证').rows.length,0);
});

test('单字口语词不拆开完整的专业词',()=>{
  const guard=[row('BAFFLE','平台未设置挡板'),row('LOCK','吊钩未设置闭锁装置')];
  assert.equal(searchHazardsDetailed(guard,'平台没挡板').rows[0]?.id,'BAFFLE');
  assert.equal(searchHazardsDetailed(guard,'吊钩没闭锁').rows[0]?.id,'LOCK');
});

test('口语缺陷词须出现在标题、别名或关键词里，正文顺带提到不算',()=>{
  const lamp=[row('NOT_SET','应设消防应急灯的场所未设置',{searchText:'应设消防应急灯的场所未设置 灯具损坏时应及时更换'})];
  assert.equal(searchHazardsDetailed(lamp,'应急灯不亮').rows.length,0);
  const broken=row('BROKEN','消防应急灯损坏');
  assert.deepEqual(searchHazardsDetailed([...lamp,broken],'应急灯不亮').rows.map(r=>r.id),['BROKEN']);
  const byKeyword=row('KW','消防应急灯不能正常点亮',{keywords:['应急灯故障']});
  assert.equal(searchHazardsDetailed([byKeyword],'应急灯坏了').rows[0]?.id,'KW');
});

test('剩下的单个实义字须在标题命中，方位字和虚化动词忽略',()=>{
  const hydrants=[row('SIGN2','消火栓无明显的标志'),row('WATER','室外消火栓水压不足')];
  assert.deepEqual(searchHazardsDetailed(hydrants,'消防栓没水').rows.map(r=>r.id),['WATER']);
  assert.equal(searchHazardsDetailed(rows,'配电箱前堆东西').rows[0]?.id,'BOX_FRONT');
  assert.equal(searchHazardsDetailed(rows,'没做应急演练').rows[0]?.id,'DRILL');
});

test('消防通道按疏散通道的同义叫法直接命中',()=>{
  const result=top('消防通道堵塞');
  assert.equal(result.matchKind,'standard');assert.equal(result.rows[0]?.id,'EXIT');
});

// 第二轮（2026-10-11）：对象和缺陷的现场叫法。标题同样取自已发布条目。
const rows2=[
  row('EXT_LOWP','灭火器失压'),
  row('EXT_HEIGHT','手提式灭火器顶部离地面高度大于1.50m'),
  row('FDOOR','人员密集场所疏散通道、楼梯及前室常闭防火门敞开'),
  row('FIREDRILL','单位灭火疏散预案或年度针对性消防演练未落实'),
  row('EBIKE','电动自行车飞线充电'),
  row('ROT','生产设备转动传动部位未设置安全防护装置'),
  row('EXLAMP','经危险区域划分需采用防爆电气的危化品暂存间仍使用非防爆灯具'),
  row('WASH','应急喷淋器或洗眼器不能提供规定流量的冲洗液，或喷淋器下方冲洗空间内有障碍物'),
  row('HWSEEP','危险废物贮存设施未采取防风、防晒、防雨、防漏、防渗、防腐等措施'),
  row('HWMIX','不相容危险废物接触或混合贮存'),
  row('DUST','粉尘涉爆企业积尘清理或如实记录不到位'),
  row('CS','有限空间作业前气体检测未覆盖必要项目'),
  row('PIT','生产作业场所可坠入的坑池井沟未设盖板或防护栏杆'),
  row('PPE','作业过程中未按规定正确佩戴和使用劳动防护用品'),
  row('OHTEST','工作场所职业病危害因素未按规定定期检测、评价'),
  row('RESP','未建立健全各级安全生产责任制'),
  row('HIDREC','隐患排查治理记录、通报不落实或重大隐患记录保存不足五年'),
  row('CONTRACT','发包出租未签安全协议且合同未明确各自安全职责'),
  row('RISK','未制定安全风险辨识管控制度或未每年开展风险辨识'),
  row('SIGNWORN','安全警示标志褪色、污损或辨识度不足'),
  row('DORM','室内储存场所违规设置员工宿舍或办公室',{searchText:'室内储存场所违规设置员工宿舍或办公室 仓库'}),
];
const top2=query=>searchHazardsDetailed(rows2,query);

test('第二轮口语问法落到对应条目',()=>{
  for(const [query,id] of [
    ['灭火器没气了','EXT_LOWP'],['灭火器放地上','EXT_HEIGHT'],['防火门常开','FDOOR'],['没做消防演练','FIREDRILL'],
    ['电瓶车乱充电','EBIKE'],['旋转部位没罩子','ROT'],['危化品库没防爆灯','EXLAMP'],['洗眼器被挡住','WASH'],
    ['危废仓库没防渗','HWSEEP'],['危废混放','HWMIX'],['积尘很厚','DUST'],['进罐没检测','CS'],['洞口没盖板','PIT'],
    ['没戴耳塞','PPE'],['没戴口罩','PPE'],['没做职业危害检测','OHTEST'],['没签责任书','RESP'],
    ['没有隐患排查记录','HIDREC'],['外包没签安全协议','CONTRACT'],['没做风险辨识','RISK'],['警示牌掉了','SIGNWORN'],
    ['仓库住人','DORM'],
  ]){
    const result=top2(query);
    assert.equal(result.matchKind,'colloquial',query);
    assert.equal(result.rows[0]?.id,id,query);
  }
});

test('消防喷淋头不落到应急喷淋器，对不上的仍不返回',()=>{
  for(const query of ['喷淋头被挡','压力表过期','气瓶没瓶帽','钢丝绳断丝','货架超载']){
    const result=top2(query);
    assert.equal(result.rows.length,0,query);assert.equal(result.matchKind,'none',query);
  }
});

test('词典外的词前面带“做、办”等虚化动词时，只按后面的词查找',()=>{
  const result=searchHazardsDetailed([row('X','未按规定开展安全评价')],'没做安全评价');
  assert.equal(result.rows[0]?.id,'X');
});
