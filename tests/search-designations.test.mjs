import test from 'node:test';
import assert from 'node:assert/strict';
import {normalize,searchHazardsDetailed,searchLawsDetailed} from '../web/js/search.js';

const law=(id,number,name='特种设备重大事故隐患判定准则')=>({id,name:`${name} ${number}`,documentNumber:number,aliases:[],searchText:`${name} ${number}`.toLowerCase(),scope:'全国',level:'国家标准',displayLevel:'国家标准',status:'现行有效'});
const hazard=(id,number,extra={})=>({id,title:'压力容器重大事故隐患判定条件',aliases:[],keywords:[],lawNames:['特种设备重大事故隐患判定准则'],stdNumbers:[number],places:[],scopes:['全国'],levels:['国家标准'],displayLevels:['国家标准'],status:'已核验',mode:'direct',category:'特种设备',displayCategory:'特种设备',searchText:`压力容器 重大事故隐患 判定条件 ${number}`.toLowerCase(),...extra});
const ids=result=>result.rows.map(x=>x.id);

test('GB designation whitespace, full-width and controlled separators share exact identity',()=>{
  const rows=[law('GOOD','GB 45067-2024'),law('NEAR','GB 450670-2024'),law('YEAR','GB 45067-2025'),law('FAMILY','GB/T 45067-2024')];
  for(const q of ['GB45067-2024','GB 45067-2024','ＧＢ４５０６７－２０２４','GB-45067_2024','GB 45067 2024','GB45067—2024'])assert.deepEqual(ids(searchLawsDetailed(rows,q)),['GOOD'],q);
  assert.deepEqual(new Set(ids(searchLawsDetailed(rows,'GB45067'))),new Set(['GOOD','YEAR']));
});

test('standard number, family, year and section do not use substring or typo expansion',()=>{
  const rows=[law('GOOD','GB 45067-2024'),law('PART','GB/T 19001.1-2024')];
  for(const q of ['GB4506','GB450670','GB45067-2023','GB/T45067-2024','GB45067-202','GB45067-20240','GB45067 202','GB45067 20','GB45067 20240','GB/T19001.2-2024'])assert.equal(searchLawsDetailed(rows,q).rows.length,0,q);
  assert.deepEqual(ids(searchLawsDetailed(rows,'GB/T 19001.1-2024')),['PART']);
});

test('GB/T formatting is recognized without conflating GB and GBZ',()=>{
  const rows=[law('T','GB/T 33000-2025'),law('GB','GB 33000-2025')];
  for(const q of ['GB/T33000','GB / T 33000','GBT33000-2025'])assert.deepEqual(ids(searchLawsDetailed(rows,q)),['T'],q);
});

test('designation match uses dedicated identities rather than incidental title or prose mentions',()=>{
  const rows=[law('GOOD','GB 45067-2024'),law('OTHER','GB 12345-2024','关于 GB45067 的说明'),law('MISSING','','关于 GB45067 的说明')];
  assert.deepEqual(ids(searchLawsDetailed(rows,'GB45067')),['GOOD']);
  const h=[hazard('GOOD','GB 45067-2024'),hazard('OTHER','GB 12345-2024',{searchText:'gb45067 重大事故隐患'})];
  assert.deepEqual(ids(searchHazardsDetailed(h,'GB45067')),['GOOD']);
});

test('standard constraints combine with keywords and active filters, never widen them',()=>{
  const rows=[hazard('PRESSURE','GB 45067-2024'),hazard('CRANE','GB 45067-2024',{title:'起重机械',searchText:'起重机械 重大事故隐患'}),hazard('OTHER','GB 12345-2024')];
  assert.deepEqual(ids(searchHazardsDetailed(rows,'GB45067 压力容器')),['PRESSURE']);
  assert.equal(searchHazardsDetailed(rows,'GB45067',{category:'消防安全'}).rows.length,0);
  assert.equal(searchHazardsDetailed(rows,'GB45067',{region:'江苏'}).rows.length,0);
  assert.equal(searchHazardsDetailed(rows,'GB45067 GB12345').rows.length,0);
});

test('major-hazard abbreviation expands even when one literal row exists, with an explanation',()=>{
  const rows=[law('TRADE','应急管理部令第10号','工贸企业重大事故隐患判定标准'),law('EQUIPMENT','GB 45067-2024'),law('LITERAL','测试文件','重大隐患资料')];
  const result=searchLawsDetailed(rows,'重大隐患');
  assert.equal(result.rows.length,3);
  assert.deepEqual(new Set(ids(result)),new Set(ids(searchLawsDetailed(rows,'重大事故隐患'))));
  assert.match(result.queryNotice,/重大隐患.*重大事故隐患.*不代表现场已构成/);
  assert.equal(searchLawsDetailed(rows,'重大事故隐患').queryNotice,'');
});

test('abbreviation expansion preserves filters and changes no hazard classification or objects',()=>{
  const rows=[hazard('EQUIPMENT','GB 45067-2024'),hazard('OTHER','GB 12345-2024',{category:'消防安全',displayCategory:'消防安全'})];
  const before=structuredClone(rows);
  assert.deepEqual(ids(searchHazardsDetailed(rows,'重大隐患',{category:'特种设备'})),['EQUIPMENT']);
  assert.equal(searchHazardsDetailed(rows,'重大隐患',{category:'重大事故隐患判定'}).rows.length,0);
  assert.deepEqual(rows,before);
});

test('abbreviation and designation constraints can be combined without using all text hits as a topic',()=>{
  const rows=[law('EQUIPMENT','GB 45067-2024'),law('UNRELATED','GB 12345-2024')];
  const result=searchLawsDetailed(rows,'重大隐患 GB45067');
  assert.deepEqual(ids(result),['EQUIPMENT']);assert.ok(result.queryNotice);
});

// Real public titles from the GB 12158-2024 recovery cohort. The standards
// mentioned inside their wording are not the rows' dedicated basis identity.
const embeddedStandardTitles=[
  ['H_12158_10_2_1','GB/T22845','如需使用手套,手套的防静电性能未符合GB/T22845的规定'],
  ['H_12158_10_2_2','GB8965.1','存在甲、乙类易燃易爆物质且有燃烧爆炸风险的作业场所，所使用的防护服未符合GB8965.1的规定'],
  ['H_12158_6_1_1','GB50058','各区域的划分未依据GB50058进行'],
  ['H_12158_9_18_1','GB/T50493','输送可燃气体的管道或容器等，未依据GB/T50493安装要求装设气体泄漏自动检测报警器'],
];

for(const [id,mentionedStandard,title] of embeddedStandardTitles){
  test(`full title retrieves ${id} without treating its embedded standard as a basis`,()=>{
    const row=hazard(id,'GB 12158-2024',{title,searchText:normalize(`${title} GB 12158-2024`)});
    const direct=hazard('DIRECT',mentionedStandard);
    const rows=[direct,row];
    const before=structuredClone(rows);
    const query=new URLSearchParams(`q=${encodeURIComponent(title)}`).get('q');
    assert.deepEqual(ids(searchHazardsDetailed(rows,query)),[id]);
    assert.deepEqual(ids(searchHazardsDetailed(rows,mentionedStandard)),['DIRECT']);
    assert.deepEqual(ids(searchHazardsDetailed(rows,'GB 12158-2024')),[id]);
    assert.equal(searchHazardsDetailed(rows,`${query} GB12345`).rows.length,0);
    assert.equal(searchHazardsDetailed(rows,query,{category:'消防安全'}).rows.length,0);
    assert.equal(searchHazardsDetailed(rows,query,{region:'江苏'}).rows.length,0);
    assert.equal(searchHazardsDetailed([{...row,status:'已失效'}],query).rows.length,0);
    assert.deepEqual(rows,before);
  });
}

test('a designation-only title still requires the dedicated standard identity',()=>{
  const title='GB/T22845';
  const row=hazard('OTHER','GB 12158-2024',{title,searchText:normalize(title)});
  assert.equal(searchHazardsDetailed([row],title).rows.length,0);
});
