import test from 'node:test';
import assert from 'node:assert/strict';
import {searchHazardIssuesDetailed} from '../web/js/search.js';
import {fieldQuantities,interpretFieldQuery} from '../web/js/query-intent.js';

// Synthetic development regressions after disclosure of the third holdout.
// These tests check subject/state mechanisms, not untouched acceptance data.
const row=(id,title,extra={})=>({id,title,searchText:title.toLowerCase(),aliases:[],keywords:[],lawNames:[],places:[],levels:[],scopes:['全国'],category:'消防安全',status:'已核验',mode:'direct',...extra});
const rows=[
  row('ext','灭火器失压'),
  row('lamp','已设置的消防应急照明灯具损坏、不能正常点亮'),
  row('sign-lamp','安全出口或疏散指示标志灯具损坏、不能正常指示'),
  row('missing-lamp','应设疏散照明的建筑部位未设置疏散照明'),
  row('exit','生产经营场所安全出口不畅通'),
  row('cylinder','气瓶放置或立放使用时未采取可靠防倾倒措施',{category:'机械设备与设施'}),
  row('wire','电气线路绝缘损坏并影响必要绝缘性能',{category:'电气安全'}),
  row('socket','插头插座接线错误或保护接地极连接不可靠',{category:'电气安全'}),
  row('rcd','电动工具回路、检修电源箱未装剩余电流动作保护装置（漏电保护器）或保护装置失效'),
  row('valve','固定式压力容器安全阀未定期校验或超过校验周期'),
  row('vessel','固定式压力容器未经定期检验或超过检验有效期'),
  row('special-inspection','特种设备未按要求办理定期检验'),
  row('failed-inspection','压力容器定期检验结论为不符合要求仍继续使用，未判定为重大事故隐患'),
  row('gauge-verify','固定式压力容器压力表未经检定或超过检定有效期'),
  row('gauge-damage','固定式压力容器压力表玻璃破裂、刻度不清或部件损坏'),
  row('gauge-mark','固定式压力容器压力表刻度盘未划出指示工作压力的红线'),
  row('strip','移动式插座（插线板）超负荷使用'),
  row('sprinkler','洒水喷头周围有遮挡或影响洒水效果的障碍物'),
  row('detector','点型火灾探测器周围0.5m内有遮挡物'),
  row('bike-entry','电动自行车或蓄电池违规进入住宅电梯、户内',{scopes:['南京']}),
  row('property','物业服务人未劝阻电动自行车进入住宅电梯',{scopes:['南京']}),
];
const search=(query,filters={})=>searchHazardIssuesDetailed(rows,query,filters);
const ids=result=>result.rows.map(item=>item.id);

test('独立问题的口语状态和转折后的省略主体保留召回',()=>{
  const two=search('灭火器没气了；应急照明灯也不亮');
  assert.equal(two.issues.length,2);assert.deepEqual(ids(two.issues[0]),['ext']);assert.deepEqual(ids(two.issues[1]),['lamp']);
  assert.deepEqual(ids(search('消防应急灯已经安装但坏了')),['lamp']);
  assert.deepEqual(ids(search('南京工厂仍在作业，安全出口从外面上了挂锁，门前的过道没有堆东西')),['exit']);
});

test('灯具跨分句继承最近的明确类型，不与普通照明或位置参照混同',()=>{
  const q='商场安全出口上方的疏散指示灯原来能亮，维修人员确认灯具坏了';
  assert.deepEqual(ids(search(q)),['sign-lamp']);
  assert.deepEqual(interpretFieldQuery(q).subjects.map(item=>item.key),['疏散指示标志']);
  for(const query of ['应急灯下面的普通照明灯坏了，应急灯正常','应急灯旁边的普通灯具坏了'])assert.ok(!ids(search(query)).includes('lamp'),query);
  assert.equal(search('应急灯正常，旁边普通照明灯在检修，维修人员确认灯具坏了。').rows.length,0);
  assert.deepEqual(ids(search('普通照明灯正常，应急灯正在检修，维修人员确认灯具坏了。')),['lamp']);
});

test('气瓶固定观察只给适用候选，其他有效固定和恢复状态不能被遗漏',()=>{
  for(const q of ['氮气钢瓶正在立着使用，瓶身就晃','氩气瓶立放，既没支架也没绑链条','气瓶没有链条']){
    const result=search(q);assert.deepEqual(ids(result),['cylinder'],q);
    assert.equal(result.issues[0].assessment.classification,'needs_conditions');
    assert.match(result.issues[0].queryNotice,/其他.*固定|替代措施/);
  }
  assert.equal(search('气瓶没有链条，不过支架固定牢固').rows.length,0);
  assert.equal(search('气瓶已经用支架固定牢固，没有绑链条。').rows.length,0);
});

test('芯线绝缘和接地端子分别继承电源线与插座，错字公开解释',()=>{
  const wire=search('二百二十伏电源线还在使用，芯线绝缘裂开，铜导体直接露在外面');
  assert.deepEqual(ids(wire),['wire']);
  assert.ok(wire.issues[0].interpretation.quantitativeFacts.includes('二百二十伏'));
  const socket=search('三孔插坐已经拆开，接地孔端子上没接地线');
  assert.deepEqual(ids(socket),['socket']);assert.match(socket.issues[0].queryNotice,/纠错/);
  assert.deepEqual(ids(search('检修电源箱从来没装过漏保')),['rcd']);
});

test('安全阀校验、容器检验和压力表检定保持独立状态',()=>{
  assert.deepEqual(ids(search('固定式压力容器本体定期检验还有效，但安全阀校验期限已经过了')),['valve']);
  const inspection=search('安全阀校验还在有效期内，但固定式压力容器本体定期检验超期');
  assert.deepEqual(ids(inspection),['vessel','special-inspection']);
  assert.equal(inspection.issues.at(-1).assessment.classification,'needs_conditions');
  assert.deepEqual(ids(search('固定式压力容器压力表检定超期，安全阀校验还在有效期内')),['gauge-verify']);
  assert.equal(search('安全阀校验还在有效期内，没有发现失灵').rows.length,0);
});

test('缺工作压力红线不能转成玻璃损坏或检定超期',()=>{
  assert.deepEqual(ids(search('固定式压力容器压力表检定还有效，玻璃没有损坏，表盘没有划工作压力红线')),['gauge-mark']);
  assert.equal(search('压力表表盘没有划工作压力红线，现在红线已补划').rows.length,0);
});

test('额定和实际负荷只比较同设备同维度数值并保留待核条件',()=>{
  for(const q of ['插线板额定十安，实测同时运行达到十六安','拖线板额定2千瓦，实际同时运行2500瓦']){
    const result=search(q);assert.deepEqual(ids(result),['strip'],q);assert.equal(result.issues[0].assessment.classification,'needs_conditions');
  }
  assert.deepEqual(fieldQuantities('十安 十六安 二百二十伏').map(item=>item.value),[10,16,220]);
  for(const q of ['插线板额定十安，实测十六瓦','插线板额定十安，实测八安','插排额定10A，另一个插排实测16A','插排额定10A，旁边电焊机实测16A。','插线板接了五样电器，还不知道额定值，也没量电流']){
    const result=search(q);assert.equal(result.rows.length,0,q);
    assert.ok(result.issues.some(issue=>issue.assessment.requiredFacts.length),q);
  }
});

test('喷头与点型烟感分别检索，使用阶段前缀不吞掉第二个问题',()=>{
  const q='零件仓库喷淋头被货物挡住；另外，装修完已经恢复使用，点型烟感包着塑料袋没拆';
  const result=search(q);assert.equal(result.issues.length,2);
  assert.deepEqual(ids(result.issues[0]),['sprinkler']);assert.deepEqual(ids(result.issues[1]),['detector']);
  assert.equal(search('点型烟感包着塑料袋，现在袋子已取下').rows.length,0);
});

test('同一设备的独立检定和损坏分组，原话保留并显式继承主体',()=>{
  const result=search('固定式压力容器压力表检定超期，玻璃也破裂');
  assert.equal(result.issues.length,2);assert.deepEqual(ids(result.issues[0]),['gauge-verify']);assert.deepEqual(ids(result.issues[1]),['gauge-damage']);
  assert.equal(result.issues[1].originalQuery,'玻璃也破裂');assert.equal(result.issues[1].interpretation.inheritedSubject.key,'压力表');
  const same=search('固定式压力容器压力表玻璃破裂，刻度也看不清');
  assert.equal(same.issues.length,1);assert.deepEqual(ids(same),['gauge-damage']);
  assert.deepEqual(ids(search('压力表检定超期，玻璃没有破裂')),['gauge-verify']);
});

test('有条件候选被筛选排除时正确解释零结果，住户与物业行为不混同',()=>{
  for(const [q,filter] of [['气瓶立放未采取可靠防倾倒措施',{category:'电气安全'}],['住户把电动自行车推入南京住宅电梯',{region:'全国'}]]){
    const result=search(q,filter);assert.equal(result.rows.length,0);assert.equal(result.issues[0].zeroReason,'filters_exclude_matches');assert.ok(result.issues[0].unfilteredCount>0);
  }
  assert.deepEqual(ids(search('住户把电动自行车推入南京住宅电梯')),['bike-entry']);
  assert.equal(search('电动自行车只在室外经过，没有进楼或挡住通道').rows.length,0);
});

test('设备已知但缺陷未知保留待核状态并提供可选择解释',()=>{
  const issue=search('电箱不合格，但不知道是接地还是箱门出了问题').issues[0];
  assert.equal(issue.rows.length,0);assert.ok(issue.suggestions.length>=2);assert.ok(issue.assessment.requiredFacts.length);
});
