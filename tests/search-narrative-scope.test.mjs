import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardIssuesDetailed, searchHazardsDetailed} from '../web/js/search.js';
import {interpretFieldQuery, splitFieldQuery} from '../web/js/query-intent.js';
import {observationStateBoundary} from '../web/js/search-boundaries.js';

// Synthetic development regressions. The second held-out pass was disclosed
// on 2026-11-08; its sentences and additional polarity reversals now exercise
// implementation defects. They are never counted as untouched holdout data.
const row=(id,title,extra={})=>({id,title,searchText:title.toLowerCase(),aliases:[],keywords:[],lawNames:[],places:[],levels:[],scopes:['全国'],category:'消防安全',status:'已核验',mode:'direct',...extra});
const rows=[
  row('ext','灭火器失压'),
  row('indicator','灭火器压力指示器的指针未在绿色范围内'),
  row('ext-block','灭火器被遮挡、取用受阻'),
  row('ext-sign','有视线障碍的灭火器设置点缺少醒目位置标志'),
  row('route','仓储场所疏散通道、安全出口或消防车通道不畅通'),
  row('lamp','已设置的消防应急照明灯具损坏、不能正常点亮'),
  row('missing-lamp','应设疏散照明的建筑部位未设置疏散照明'),
  row('staff','消防控制室未实行24小时双人值班或值班人员未持证'),
  row('limiter','桥式、门式起重机未按规定安装起升高度限位装置'),
  row('limiter-fault','起重机高度限位器损坏'),
  row('gauge-damage','固定式压力容器压力表玻璃破裂、刻度不清或部件损坏'),
  row('gauge-expired','固定式压力容器压力表未经检定或超过检定有效期'),
  row('box-ground','装有电器的可开启配电箱（柜）门与金属框架未可靠连接'),
  row('box-block','配电箱（柜）前堆放杂物，操作通道或维护空间被遮挡、占用'),
  row('box-label','配电装置安全标志牌被贴纸等遮挡',{keywords:['配电箱']}),
  row('helmet','作业人员在应佩戴安全帽的作业场所未佩戴安全帽'),
  row('bike','电动自行车飞线充电',{scopes:['南京']}),
];
const search=(q,filters={})=>searchHazardIssuesDetailed(rows,q,filters);
const ids=result=>result.rows.map(row=>row.id);

test('条件前缀和共享部件说明不被切成独立隐患',()=>{
  for(const q of [
    '做固定式压力容器年度检查时发现，储气罐压力表的玻璃裂了，刻度也看不清。',
    '年度检查固定式压力容器时，压力表玻璃裂开了，刻度模糊不清。',
  ]){
    assert.equal(splitFieldQuery(q).length,1,q);
    assert.deepEqual(ids(search(q)),['gauge-damage'],q);
  }
});

test('场所和母设备不会成为必须同时命中标题的第二个设备',()=>{
  const samples=[
    ['采用集中火灾报警系统的厂区，消控室夜班一直只有一个人在岗。',['staff']],
    ['安全出口原来装好的消防应急照明灯也坏了，断电试验一点都不亮。',['lamp']],
    ['配电箱旁放着灭火器，灭火器没有压力。',['ext','indicator']],
  ];
  for(const [q,expected] of samples)assert.deepEqual(ids(search(q)),expected,q);
  const intent=interpretFieldQuery(samples[1][0]);
  assert.deepEqual(intent.subjects.map(object=>object.key),['应急灯']);
  assert.ok(intent.contextObjects.some(object=>object.key==='安全出口'));
});

test('检定超期与否认损坏、损坏与否认超期的作用域各自保留',()=>{
  for(const q of [
    '固定式压力容器上的压力表还在用，检定证书上的有效期已经过了三个月，表本身并没有损坏。',
    '固定式压力容器压力表检定超期，但表本身没有损坏。',
    '固定式压力容器压力表玻璃没有破裂，但检定证书过期了。',
  ])assert.deepEqual(ids(search(q)),['gauge-expired'],q);
  for(const q of [
    '固定式压力容器压力表玻璃破裂，但检定没有超期。',
    '固定式压力容器压力表已经损坏，但是否检定超期尚未核实。',
    '固定式压力容器压力表玻璃破裂，检定是否超期尚未核实。',
  ])assert.deepEqual(ids(search(q)),['gauge-damage'],q);
});

test('被字句中的否定和多个正常状态不能转成堵塞或失压',()=>{
  for(const q of [
    '安全出口和疏散通道也没有被杂物堵住。',
    '仓库疏散通道未被纸箱堵塞。',
    '疏散通道没有再次被货物堵塞。',
    '走了一圈，灭火器压力正常，安全出口和疏散通道也没有被杂物堵住。',
    '固定式压力容器压力表检定还在有效期内，玻璃完整、刻度清楚，检查没有发现损坏。',
  ]){
    const result=search(q);assert.equal(result.rows.length,0,q);
    assert.ok(result.issues.every(issue=>issue.assessment.classification==='fact_unconfirmed'),q);
  }
});

test('明确疏散用途的口语过道和通行障碍能找到对应候选',()=>{
  for(const q of [
    '纸箱一摞摞放在仓库供人员疏散的过道里，现在人都过不去了。',
    '仓库用于人员疏散的走道被周转箱占用，无法通行。',
  ])assert.deepEqual(ids(search(q)),['route'],q);
  assert.equal(search('过道塞满东西').issues[0].assessment.classification,'needs_conditions');
});

test('机型年份和额定参数不阻断召回，数值保留为待核适用条件',()=>{
  const q='车间这台桥式天车是2025年设计制造的，额定10吨、起升6米，没有装过任何起升高度限位器。';
  const issue=search(q).issues[0];
  assert.deepEqual(ids(issue),['limiter']);
  assert.equal(issue.originalQuery,q);
  assert.deepEqual(issue.interpretation.quantitativeFacts,['2025年','10吨','6米']);
  assert.equal(issue.assessment.classification,'needs_conditions');
  assert.match(issue.queryNotice,/不代表已满足|不会自动证明/);
  assert.ok(!issue.rows.some(row=>row.id==='limiter-fault'));
  assert.equal(search(q,{region:'南京'}).rows.length,0);
});

test('缺少保护连接按箱门条件查找，不丢失装有电器这一限定',()=>{
  const q='装着按钮和指示灯的可开启金属配电柜门，门板和金属框架接地端子之间没有保护连接。';
  const issue=search(q).issues[0];
  assert.deepEqual(ids(issue),['box-ground']);
  assert.equal(issue.assessment.classification,'needs_conditions');
  assert.match(issue.queryNotice,/装有电器/);
});

test('明确作业中的未佩戴可召回，单纯把备用帽子放旁边不造出未佩戴',()=>{
  const q='车间已经按头部撞击风险规定这个岗位必须戴安全帽，可刚才那位师傅为了凉快，帽子放在一边就开工了。';
  const issue=search(q).issues[0];
  assert.deepEqual(ids(issue),['helmet']);assert.equal(issue.assessment.classification,'needs_conditions');
  assert.equal(search('安全帽已戴好，备用帽子放在一边。').rows.length,0);
});

test('两个独立设备保留各自说明，分号先于共享部件逗号切分',()=>{
  const q='生产车间电箱前塞满周转料，柜门开不了；疏散出口原来装好的消防应急照明灯也坏了，断电试验一点都不亮。';
  const result=search(q);
  assert.equal(result.issues.length,2);
  assert.equal(result.issues[0].query,'生产车间电箱前塞满周转料，柜门开不了');
  assert.deepEqual(ids(result.issues[0]),['box-block']);
  assert.deepEqual(ids(result.issues[1]),['lamp']);
  const second=search('厂房灭火器被货物挡住拿不出来；另外年度检查固定式压力容器时，看到储气罐压力表玻璃已经破裂。');
  assert.equal(second.issues.length,2);
  assert.deepEqual(ids(second.issues[0]),['ext-block']);
  assert.deepEqual(ids(second.issues[1]),['gauge-damage']);
});

test('未知报警类型虽保持事实未核实，仍提供可选解释',()=>{
  const issue=search('仓库的报警装置好像有问题，现场还没说明是哪一种报警，也没说清哪里不对。').issues[0];
  assert.equal(issue.rows.length,0);assert.equal(issue.assessment.classification,'fact_unconfirmed');
  assert.ok(issue.suggestions.length>=2);assert.ok(issue.assessment.requiredFacts.length);
});

test('灭火器的压力指示器不改匹配为压力容器压力表',()=>{
  const issue=search('巡检拍到这只灭火气压力表的针已经落到欠压红区了，还摆在车间里。').issues[0];
  // H2_01 originally labelled only the generic “灭火器失压”. The more
  // specific pressure-indicator candidate is deliberately preserved instead.
  assert.deepEqual(ids(issue),['indicator']);
  assert.match(issue.queryNotice,/纠错/);
});

test('长句自然语言回退仍服从明确地域与专业筛选',()=>{
  const q='南京小区的电动自行车飞线充电';
  assert.deepEqual(ids(search(q)),['bike']);
  const excluded=search(q,{region:'全国'}).issues[0];
  assert.equal(excluded.rows.length,0);assert.equal(excluded.zeroReason,'filters_exclude_matches');
  assert.equal(excluded.unfilteredCount,1);
});

test('单字断的否定保持有效，断路器与断电不被误认为否定断线',()=>{
  const records=[row('wire','地线断开')];
  for(const q of ['地线没有断','接地线没有断。','地线没有断了']){
    assert.equal(searchHazardsDetailed(records,q).rows.length,0,q);
    const result=searchHazardIssuesDetailed(records,q);
    assert.equal(result.rows.length,0,q);
    assert.equal(result.issues[0].assessment.classification,'fact_unconfirmed',q);
    assert.match(result.issues[0].queryNotice,/状态词/);
  }
  assert.equal(observationStateBoundary('配电箱没有断路器'),null);
  assert.equal(observationStateBoundary('检修前没有断电'),null);
});

test('共享否定、待核与排除范围不能在并列切分后变成第二项肯定事实',()=>{
  for(const q of [
    '没有发现灭火器失压和应急灯损坏',
    '尚未核实灭火器失压和应急灯损坏',
    '已排除灭火器失压和应急灯损坏',
    '本次巡查未查出灭火器失压以及消防应急照明灯损坏',
  ]){
    assert.equal(searchHazardsDetailed(rows,q).rows.length,0,q);
    const result=search(q);assert.equal(result.rows.length,0,q);
    assert.ok(result.issues.every(issue=>issue.assessment.classification==='fact_unconfirmed'),q);
  }
  for(const q of ['没有发现灭火器失压，但应急灯确实损坏','尚未核实灭火器失压，但应急灯已确认损坏']){
    const result=search(q);assert.deepEqual(ids(result),['lamp'],q);
  }
  const positive=search('灭火器失压和应急灯损坏');
  assert.equal(positive.issues.length,2);assert.deepEqual(ids(positive),['ext','lamp']);
});

test('历史事实和当前恢复按对象覆盖，另一设备修复不能取消已观察的问题',()=>{
  for(const q of ['灭火器以前失压，现在压力正常','灭火器失压，现在压力正常','灭火器以前失压']){
    assert.equal(searchHazardsDetailed(rows,q).rows.length,0,q);
    assert.equal(search(q).rows.length,0,q);
  }
  for(const q of ['灭火器曾经修复，现在又失压','灭火器失压，应急灯已修复']){
    const result=search(q);assert.ok(ids(result).includes('ext'),q);
    assert.ok(!ids(result).includes('lamp'),q);
  }
  assert.deepEqual(ids(search('固定式压力容器压力表玻璃破裂，但刻度清楚')),['gauge-damage']);
  assert.deepEqual(ids(search('固定式压力容器压力表指针损坏，但玻璃完整')),['gauge-damage']);
  assert.deepEqual(ids(search('固定式压力容器压力表检定超期，表本身已修复')),['gauge-expired']);
});

test('证据不足、无法确认或不能排除不等于已确认，但已确认的独立事实可继续检索',()=>{
  for(const q of ['没有证据表明灭火器失压','暂无证据证明灭火器失压','还不能确认应急灯损坏','无法证实应急灯损坏','不能排除灭火器失压']){
    assert.equal(searchHazardsDetailed(rows,q).rows.length,0,q);
    const result=search(q);assert.equal(result.rows.length,0,q);
    assert.ok(result.issues.every(issue=>issue.assessment.classification==='fact_unconfirmed'),q);
  }
  for(const q of ['现在已经确认应急灯损坏','没有证据表明灭火器失压，但复查确认应急灯损坏']){
    assert.deepEqual(ids(search(q)),['lamp'],q);
  }
});

test('位置参照设备不能承接另一个未识别对象的故障，反向状态也不覆盖已知对象',()=>{
  for(const q of ['应急灯下面的普通照明灯坏了，应急灯正常','应急灯上方的普通照明灯坏了','应急灯旁边的窗户破裂']){
    const result=search(q);
    assert.ok(!ids(result).includes('lamp'),q);
    assert.equal(result.issues[0].assessment.reason,'observed_object_unidentified',q);
  }
  assert.deepEqual(ids(search('应急灯坏了，下面的普通照明灯正常')),['lamp']);
  assert.deepEqual(ids(search('安全出口下面的消防应急照明灯坏了')),['lamp']);
});
