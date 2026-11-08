import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardsDetailed, searchHazardIssuesDetailed} from '../web/js/search.js';
import {splitFieldQuery, interpretFieldQuery, fieldObjects} from '../web/js/query-intent.js';

// Synthetic development examples, not anonymised enterprise records or a
// held-out acceptance dataset. Deliberate distractors exercise semantic edges.
const row=(id,title,extra={})=>({id,title,searchText:title.toLowerCase(),aliases:[],keywords:[],lawNames:[],places:[],levels:[],scopes:['全国'],category:'消防安全',status:'已核验',mode:'direct',...extra});
const rows=[
  row('H_LOSS','灭火器失压'),
  row('H_EXT_BAD','灭火器损坏'),
  row('H_ROUTE','疏散通道、安全出口或消防车通道被占用、堵塞、封闭'),
  row('H_SPRAY','喷涂区内货物堆放阻塞疏散通道'),
  row('H_CHEM_ROUTE','危险化学品使用场所疏散通道被占用或设置逃生障碍'),
  row('H_LOCAL_ROUTE','纸箱堆积、占用疏散通道',{scopes:['南京']}),
  row('H_HYDRANT','消火栓被遮挡、圈占'),
  row('H_LAMP_BAD','已设置的消防应急照明灯具损坏、不能正常点亮',{aliases:['应急灯不亮','应急灯坏了']}),
  row('H_LAMP_ABSENT','应设疏散照明的建筑部位未设置疏散照明',{searchText:'应设疏散照明的建筑部位未设置疏散照明 应急灯 安装后损坏 故障'}),
  row('H_BOX_SIGN','配电箱未设置警示标志',{category:'电气安全'}),
  row('H_BOX_GROUND','装有电器的可开启配电箱（柜）门与金属框架未可靠连接',{category:'电气安全',searchText:'装有电器的可开启配电箱（柜）门与金属框架未可靠连接 配电箱 保护接地'}),
  row('H_BOX_BLOCK','配电箱前堆放杂物、操作通道被占用',{category:'电气安全'}),
  row('H_CRANE','起重机吊钩防脱钩装置损坏'),
  row('H_BIKE','电动自行车飞线充电',{searchText:'电动自行车飞线充电 起重机吊钩防脱钩装置损坏 只是无关正文'}),
  row('H_BIKE_SITE','电动自行车集中充电场所防火分隔不符合要求'),
  row('H_ALARM_ABSENT','生产设备上易发生故障或危险性较大区域未配置报警装置'),
];
const search=(query,filters={})=>searchHazardIssuesDetailed(rows,query,filters);
const ids=items=>items.map(item=>item.id);

test('多问题按各自对象与缺陷分组，不把整句作为同时满足的条目',()=>{
  for(const query of ['灭火器失压，疏散通道还堆了纸箱','灭火器没压力；疏散通道堵塞','灭活器没压力，而且消防栓被挡住了','灭火器失压和疏散通道堵塞']) {
    const result=search(query);
    assert.equal(result.isMultiIssue,true,query);assert.equal(result.issues.length,2,query);
    assert.ok(result.issues[0].rows.some(row=>row.id==='H_LOSS'),query);
    assert.ok(result.issues[1].rows.some(row=>['H_ROUTE','H_HYDRANT'].includes(row.id)),query);
    assert.ok(result.rows.length>=2,query);
  }
});

test('正式完整标题和一个问题的补充描述不被标点误拆',()=>{
  const title=rows.find(row=>row.id==='H_ROUTE').title;
  const result=search(title);assert.equal(result.isMultiIssue,false);assert.deepEqual(ids(result.rows),['H_ROUTE']);
  assert.equal(splitFieldQuery('检查发现，灭火器没压力，指针在红色区域').length,1);
  assert.equal(splitFieldQuery('疏散通道、安全出口或消防车通道被占用、堵塞、封闭').length,1);
});

test('长句清理保留原话、地点和状态，词序变化仍返回对题候选',()=>{
  for(const query of ['今天检查时看到车间里的灭火器没有压力了','请帮我查一下，灭火器一点压力都没有，怎么整改','在仓库里灭火器没压力了','失压的灭火器','安装后应急灯坏了']) {
    const result=search(query),issue=result.issues[0];
    assert.equal(issue.originalQuery,query);
    assert.ok(issue.rows.some(row=>['H_LOSS','H_LAMP_BAD'].includes(row.id)),query);
    assert.ok(!issue.rows.some(row=>row.id==='H_LAMP_ABSENT'),query);
  }
  const meaning=interpretFieldQuery('今天检查时看到车间里的灭火器没有压力了');
  assert.equal(meaning.query,'灭火器失压');assert.ok(meaning.scenes.includes('车间'));
});

test('明确未发生、待核实、已修复均不因口语清理变成当前缺陷',()=>{
  for(const query of ['应急灯没有坏','通道没有堆东西','通道没放杂物','疏散通道未堵塞','灭火器没有失压','灭火器不失压','压力表不是检定超期','今天检查时看到灭火器好像没有压力了','现场尚未核实应急灯是否损坏','灭火器已经修复了','灭火器没压力但已更换','压力表没有超过检定有效期']) {
    for(const result of [searchHazardsDetailed(rows,query),search(query).issues[0]]) {
      assert.equal(result.rows.length,0,query);assert.equal(result.assessment.classification,'fact_unconfirmed',query);
    }
  }
  const result=search('灭火器没有损坏，疏散通道堵塞');
  assert.equal(result.issues[0].rows.length,0);assert.ok(result.issues[1].rows.some(row=>row.id==='H_ROUTE'));
  assert.ok(search('灭火器已经修复但还是没压力').rows.some(row=>row.id==='H_LOSS'));
});

test('未安装对象与已有设备故障、其他附件未设置分开',()=>{
  assert.equal(search('电箱没安装').rows.length,0);
  assert.equal(searchHazardsDetailed(rows,'电箱没安装').rows.length,0);
  const bad=search('安装后应急灯坏了');
  assert.deepEqual(ids(bad.rows),['H_LAMP_BAD']);
  assert.ok(!searchHazardsDetailed(rows,'报警装置损坏').rows.some(row=>row.id==='H_ALARM_ABSENT'));
  const missing=search('应急灯没有安装');
  assert.equal(missing.rows.length,0);assert.equal(missing.issues[0].assessment.classification,'needs_conditions');
  assert.ok(missing.issues[0].suggestions.some(choice=>choice.query.includes('未设置')));
});

test('资料未提供只能触发资料与实施事实核实，不能转换成未实施',()=>{
  for(const query of ['检查记录暂时没给我们','设备检验报告没有提供','未见年度检测报告','没有找到培训记录']) {
    const issue=search(query).issues[0];assert.equal(issue.rows.length,0,query);
    assert.equal(issue.assessment.classification,'needs_conditions',query);
    assert.ok(issue.assessment.requiredFacts.length,query);
  }
});

test('设备对象完整识别，行车和自行车不交叉，泛称故障先问部件',()=>{
  assert.deepEqual(fieldObjects('电动自行车飞线充电').map(item=>item.key),['电动自行车']);
  assert.deepEqual(fieldObjects('行车吊钩损坏').map(item=>item.key),['起重机','吊钩']);
  assert.deepEqual(ids(search('行车吊钩损坏').rows),['H_CRANE']);
  assert.ok(search('自行车充电').rows.every(row=>row.id!=='H_CRANE'));
  const vague=search('行车坏了').issues[0];assert.equal(vague.rows.length,0);assert.equal(vague.assessment.classification,'needs_conditions');
});

test('含糊通道提供用途选择，明确疏散通道优先通用场景',()=>{
  const ambiguous=search('通道堆东西').issues[0];
  assert.equal(ambiguous.rows.length,0);assert.equal(ambiguous.assessment.reason,'passage_use_unconfirmed');
  assert.equal(ambiguous.suggestions.length,3);assert.ok(ambiguous.assessment.requiredFacts.includes('通道实际用途'));
  const explicit=search('疏散通道堆满了纸箱');assert.equal(explicit.rows[0].id,'H_ROUTE');
  const selected=search(ambiguous.suggestions[0].query);assert.equal(selected.rows[0].id,'H_ROUTE');
});

test('电箱接地候选明确箱门、保护导体和场景条件',()=>{
  const issue=search('电箱没接地').issues[0];
  assert.equal(issue.assessment.classification,'needs_conditions');
  assert.ok(issue.assessment.requiredFacts.some(text=>text.includes('箱门')));
  assert.ok(issue.suggestions.some(choice=>choice.query.includes('保护接地线')));
  assert.ok(!issue.rows.some(row=>row.id==='H_BOX_BLOCK'||row.id==='H_BOX_SIGN'));
});

test('缺陷或设备仅在正文出现不能抢占结果',()=>{
  const distractor=row('H_BODY','消火栓被遮挡',{searchText:'消火栓被遮挡 灭火器失压 没压力'});
  const found=searchHazardIssuesDetailed([distractor,...rows],'灭火器没压力');
  assert.ok(found.rows.some(row=>row.id==='H_LOSS'));assert.ok(!found.rows.some(row=>row.id==='H_BODY'));
});

test('同一筛选应用到每个问题，零结果区分筛选排除和库内未匹配',()=>{
  const result=search('灭火器没压力，配电箱前堆物',{category:'电气安全'});
  const [fire,electric]=result.issues;
  assert.equal(fire.rows.length,0);assert.equal(fire.zeroReason,'filters_exclude_matches');assert.ok(fire.unfilteredCount>0);
  assert.ok(electric.rows.every(row=>row.category==='电气安全'));assert.ok(electric.rows.length);
  const absent=search('不存在于词库的机器异常').issues[0];assert.equal(absent.zeroReason,'no_library_match');
});

test('明确标准编号约束不会被自然语言回退丢弃',()=>{
  const constrained=[row('H_A','灭火器失压',{stdNumbers:['GB 50016-2014']}),row('H_B','灭火器失压',{stdNumbers:['GB 55037-2022']})];
  const found=searchHazardIssuesDetailed(constrained,'GB 50016-2014 灭火器没压力');
  assert.deepEqual(ids(found.rows),['H_A']);
});

test('受控错字公开解释，原词已有对应对象时不强行纠错',()=>{
  const corrected=search('灭活器没压力').issues[0];
  assert.ok(corrected.rows.some(row=>row.id==='H_LOSS'));assert.match(corrected.queryNotice,/纠错/);
  const literal=row('H_LITERAL','灭活器检查');
  const found=searchHazardIssuesDetailed([literal,row('H_OTHER','灭火器检查')],'灭活器');
  assert.deepEqual(ids(found.rows),['H_LITERAL']);
});

test('每组给出可用于高亮的语义词且重复候选不污染总数',()=>{
  const result=search('灭火器没压力，灭火器失压');
  assert.equal(result.issues.length,2);assert.deepEqual(ids(result.rows),['H_LOSS']);
  assert.ok(result.issues[0].highlightTerms.includes('灭火器'));
  assert.ok(result.issues[0].highlightTerms.some(term=>term.includes('失压')));
});

// Disclosed after the first separate acceptance pass on 2026-11-08. These are
// now regression examples, never counted as an untouched holdout again.
test('首次留出验收发现的口语和零结果说明缺口已转入回归',()=>{
  const charging=search('电动自行车拉线充电').issues[0];
  assert.ok(charging.rows.some(row=>row.id==='H_BIKE'));
  assert.ok(charging.rows.every(row=>row.id!=='H_BIKE_SITE'));
  assert.equal(charging.assessment.classification,'needs_conditions');
  assert.match(charging.queryNotice,/地域/);
  for(const query of ['压力表检定证书没有拿出来','配电箱还没有安装']) {
    const result=search(query).issues[0];
    assert.equal(result.rows.length,0,query);
    assert.equal(result.assessment.classification,'needs_conditions',query);
    assert.ok(result.queryNotice,query);
  }
  const gap=search('普通工业车间地面油污').issues[0];
  assert.equal(gap.rows.length,0);
  assert.equal(gap.assessment.classification,'evidence_gap');
});

test('危化场所通信和报警的设置与失效分支可独立找到',()=>{
  const records=[
    row('H_ABSENT','危险化学品生产储存场所未设置通信装置或报警装置'),
    row('H_ALARM','危险化学品生产储存场所报警装置失效'),
    row('H_COMM','危险化学品生产储存场所通信装置失效'),
  ];
  assert.deepEqual(ids(searchHazardIssuesDetailed(records,'危险化学品生产储存场所没有报警装置').rows),['H_ABSENT']);
  assert.deepEqual(ids(searchHazardIssuesDetailed(records,'危险化学品生产储存场所通信装置失效').rows),['H_COMM']);
  assert.deepEqual(ids(searchHazardIssuesDetailed(records,'危险化学品生产储存场所报警装置失效').rows),['H_ALARM']);
});
