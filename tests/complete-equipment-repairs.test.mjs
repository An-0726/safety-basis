import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import { normativeContentText, renderNormativeContent, validateNormativeClause } from '../web/js/normative-content.js';
const root = new URL('../', import.meta.url);
const read = (path) => JSON.parse(fs.readFileSync(new URL(path, root)));
const entity = (kind,id) => read(`knowledge/${kind}/${id}.json`);
const report = read('docs/complete-equipment-author-20261005.json');
const review = (kind,id) => entity(`reviews/${kind}`,id);
function canonical(x) {
  if (Array.isArray(x)) return x.map(canonical);
  if (x && typeof x === 'object') return Object.fromEntries(Object.keys(x).filter(k=>k!=='canonicalHash').sort().map(k=>[k,['aliases','places','keywords'].includes(k) && Array.isArray(x[k]) ? [...x[k]].sort() : canonical(x[k])]));
  return x;
}
const hash = x => crypto.createHash('sha256').update(JSON.stringify(canonical(x))).digest('hex');

test('equipment author review binds exact entity and retains original identity metadata',()=>{
  for (const path of report.authoredFiles.filter(x=>x.startsWith('knowledge/reviews/'))) {
    const rv=read(path); const kind=path.split('/')[2]; const d=entity(kind,rv.entityId);
    assert.equal(rv.reviewedContentHash,hash(d),path);
    if(kind==='links') {
      assert.equal(rv.contextHashes.hazard,hash(entity('hazards',d.hazardId)),path);
      assert.equal(rv.contextHashes.clause,hash(entity('clauses',d.clauseId)),path);
    }
    if(rv.previousDefinition && kind==='hazards') {
      for(const field of ['id','aliases','keywords','category','places']) assert.deepEqual(d[field],rv.previousDefinition[field],`${rv.entityId}:${field}`);
    }
    for(const e of rv.evidenceRefs) if(e.startsWith('E_')||e.startsWith('EH_')) assert.equal(entity('evidence',e).id,e);
  }
});

test('all 40 verified equipment candidate branches preserve stable IDs and are active',()=>{
  const expected=['H011','H_108B10FED8E24D248155616659','H_15607_4_3_2_1','H_15607_4_3_3_1','H_15607_4_3_3_2','H_15607_4_4_4_1','H_15607_4_5_1_1','H_15607_4_6_1','H_15607_4_8_2_1','H_15607_5_1_1_1','H_15607_5_1_4_1','H_15607_5_2_1_2','H_15607_5_2_3_1','H_15607_5_2_6_1','H_15607_6_3_1','H_15607_6_4_1','H_15607_6_6_1','H_15607_7_3_1','H_15607_7_4_1','H_15607_8_1_1','H_15607_8_2_1','H_15607_8_2_2','H_15607_8_3_1','H_15607_8_4_1','H_15607_8_5_1','H_15607_8_6_1','H_15607_8_6_2','H_374AD1DFC5D74D438D1E71C692','H_436E5794B5564E46BB6E6FBB14','H_8855020E458243468B914D2815','H_AC0F88BA4D1D4C1B8534AA9D95','H_C00BAD75E6D54B00B332B38AFC','H_C469E27A43B948799AAF85BA8C','H_D52A0DF6DCCD445DBB79FBC35F','H_GB12801_5_4_6_2','H_GBT47236_4_2_2_3','H_GBT47236_4_2_3_1_3','H_GBT47236_4_2_4_2_1','H_GBT47236_4_2_7_1_1','H_GBT47236_4_3_4_1'];
  assert.equal(expected.length,40);
  for(const id of expected){ const h=entity('hazards',id);assert.equal(h.lifecycle,'active',id);assert.equal(h.mode,'direct',id);assert.ok(review('hazards',id).previousDefinition,id); }
  for(const id of ['H_15607_4_6_1','H_15607_6_4_1','H_D52A0DF6DCCD445DBB79FBC35F','H_AC0F88BA4D1D4C1B8534AA9D95','H_GBT47236_4_2_3_1_3']) assert.ok(review('hazards',id).remainingUnsupportedBranches.length,id);
});

test('powder thresholds, sequence and exceptions do not broaden the current rule',()=>{
  const h=entity('hazards','H_15607_4_3_2_1');assert.match(h.description,/除喷枪出口等局部区域外/u);assert.match(h.description,/50%/u);assert.match(h.description,/10 g\/m³/u);assert.match(h.description,/未知爆炸下限/u);
  const ground=entity('hazards','H_15607_4_8_2_1');assert.match(ground.description,/1×10⁶ Ω/u);assert.match(ground.conditions,/静电消除器/u);assert.doesNotMatch(ground.description,/100 Ω/u);
  const stop=entity('hazards','H_15607_8_2_2');assert.match(stop.measures,/先停高压静电发生器和喷粉装置，5 min～10 min后再关闭排风机/u);
  const person=entity('hazards','H_15607_8_8_1');assert.match(person.description,/任何部分/u);assert.match(person.conditions,/工艺需求/u);assert.match(person.conditions,/可靠.*安全防护/u);
  assert.doesNotMatch(entity('links','K_XLSX_WEB_H_5F9C57C38B654926B89B0AC22E').applicability,/生产中易产生静电/u);
  for(const id of ['C_XLSX_WEB_28DB9161801CEF8D53AA66A0','C_XLSX_WEB_6690FA6FD060E6B076AAC189','C_XLSX_WEB_94075F0B9065D34951346F1F']) assert.doesNotMatch(entity('clauses',id).quote,/附录|表C|References|参考文献/u);
});

test('all existing caster consumers are design-manufacture-acceptance scoped and recommendatory',()=>{
  const rows=report.decisions.filter(x=>x.action==='active_dependency_repair' && (x.hazardId.startsWith('H_GBT47236_')||x.hazardId==='H_F8BD176AF46643EA9E3CC56A6F'));
  assert.equal(rows.length,44);
  for(const row of rows){ const h=entity('hazards',row.hazardId);assert.match(h.conditions,/设计、制造和验收/u);assert.match(h.conditions,/推荐性/u);assert.match(h.conditions,/不适用于压铸机和压铸单元/u);assert.doesNotMatch(h.note,/适用对象为低压铸造机及其他金属型铸造设备的使用与维护现场/u); }
  assert.doesNotMatch(entity('hazards','H_GBT47236_4_2_3_1_3').description,/安全距离/u);
  assert.match(entity('hazards','H_GBT47236_4_2_4_2_1').description,/资料或检测/u);
  assert.match(entity('hazards','H_GBT47236_4_2_11_1_1').measures,/措施示例/u);
});

test('caster Table3 retains full table semantics and fails on lost cells',()=>{
  const c=entity('clauses','C_GBT47236_4_3_4');assert.equal(normativeContentText(c.contentParts),c.quote);
  assert.deepEqual(validateNormativeClause(c),['T_ALL_GBT47236_2026_3']);
  const table=c.contentParts[1];assert.equal(table.columnCount,5);assert.equal(table.bodyRows.length,3);
  for(const s of ['主运动机构因驱动源失效','停止运行时自动锁定','倾转到位应有机械限位','4.2.2.7','表B.1中序号10'])assert.ok(c.quote.includes(s),s);
  assert.match(renderNormativeContent(c),/rowspan="2"/u);
  const bad=structuredClone(c);bad.contentParts[1].bodyRows[2]=[];assert.throws(()=>renderNormativeContent(bad));
  assert.deepEqual(review('clauses',c.id).reviewedTableIds,['T_ALL_GBT47236_2026_3']);
});

test('coating and grounding misbindings have exact replacement sources',()=>{
  assert.equal(entity('links','K_604e31903924e6e2a8ee898a').lifecycle,'retired');
  assert.equal(entity('links','K_C375310B40228B45804B8F').clauseId,'C_GB14444_5_3_1');
  assert.equal(entity('links','K_XLSX_WEB_H_489DF59DA4DF4E89B50C321130').clauseId,'C_ALL_GB6514_6_2_2_2');
  assert.equal(entity('links','K_XLSX_WEB_H_62ACB71A70BA4BFDB59436E29F').clauseId,'C_XLSX_WEB_A0DE802DADFC9DAB2C301F5F');
  assert.equal(entity('links','K_XLSX_WEB_H_FBCF449DEB7E4FF380E96780D6').clauseId,'C_15607_6_5');
  assert.equal(entity('links','K_XLSX_WEB_H_12158_8_1_20_2').clauseId,'C_12158_8_1_20');
  assert.match(entity('clauses','C_12158_4_2_2_1').quote,/对地绝缘的静电导体应接地/u);
  assert.doesNotMatch(entity('clauses','C_12158_4_2_2_1').quote,/调漆|回流/u);
  for(const id of ['H011','H_AC0F88BA4D1D4C1B8534AA9D95','H_489DF59DA4DF4E89B50C321130'])assert.match(entity('hazards',id).conditions,/不适用于桥梁、建筑物、大型储罐、船舶/u);
  for(const id of ['H_0D7B747137B74DEEA766A4DA5E','H_D86D43777C5E41FB8680FAD1A0'])assert.equal(entity('hazards',id).lifecycle,'proposed');
});

test('precise MEM10 and other scope restrictions survive in H/K',()=>{
  for(const id of ['H_CF_MAJOR_01','H_CF_MAJOR_08'])assert.match(entity('hazards',id).conditions,/存在粉尘爆炸危险的工贸企业/u);
  assert.match(entity('links','K_CF_MAJOR_01_C_PDDB_11').applicability,/第（三）项/u);assert.match(entity('links','K_CF_MAJOR_08_C_PDDB_11').applicability,/第（六）项/u);
  assert.doesNotMatch(entity('hazards','H_CF_MAJOR_01').measures,/加装泄爆、隔爆或自动抑爆/u);
  assert.match(entity('hazards','H_CF_MAJOR_08').measures,/不限定.*唯一/u);
  assert.match(entity('hazards','H_AA6382B9890B42B1B70DC3EA3B').conditions,/仅适用于机械企业/u);
  assert.match(entity('hazards','H_C00BAD75E6D54B00B332B38AFC').conditions,/新建、扩建和改建/u);assert.match(entity('hazards','H_C00BAD75E6D54B00B332B38AFC').conditions,/推荐性/u);
  assert.match(entity('hazards','H_8855020E458243468B914D2815').conditions,/不适用于化工、采矿、隧道、烟花爆竹及民用爆破器材/u);
  assert.equal(entity('law-versions','LV_STD_GB14444').officialName,'喷漆室安全技术要求');assert.equal(entity('law-versions','LV_STD_GB14443_2025').officialName,'涂层烘干室安全技术要求');
  assert.equal(entity('law-versions','LV_STD_GB14443_2025').effectiveDate,'2026-08-01');
});

test('unresolved branches and source candidates are not cleared by lifecycle edits',()=>{
  for(const id of ['H_15577_6_3_3_1','H_CF_GEN_03','H_CF_GEN_07','H_GBT47236_4_3_2_1','H_GBT47236_4_3_3_1','H_GBT47236_4_3_5_1','H_GBT47236_4_3_6_1'])assert.equal(entity('hazards',id).lifecycle,'proposed');
  assert.ok(report.partialCanonicalMappings.every(x=>x.wholeCandidateAdmitted===false));
  assert.equal(report.originalPdfsPublished,false);assert.equal(report.siteFactsConfirmed,false);assert.equal(report.formalApproval,false);
});

test('negative examples preserve smooth floors and protected process-required entry',()=>{
  const floor=entity('hazards','H_15607_4_3_3_2');assert.equal(floor.description,'喷粉区地面不平整或不光滑，或存在缝隙、凹槽。');
  assert.match(review('hazards',floor.id).negativeCase,/平整、光滑且无缝隙和凹槽，不触发/u);
  const entry=entity('hazards','H_15607_8_8_1');assert.match(entry.description,/在不满足本条工艺需求进入例外的情形下/u);
  assert.match(entry.conditions,/满足例外的进入不作为本项缺陷/u);
  assert.match(review('hazards',entry.id).negativeCase,/已采取可靠安全防护并符合GB6514相关规定.*不触发/u);
});

test('AQ4273 quote retains historical reference while current H uses the successor boundary',()=>{
  const c=entity('clauses','C_ALL_AQ4273_4_10');assert.match(c.quote,/GB 7231/u);
  const h=entity('hazards','H_8855020E458243468B914D2815');assert.match(h.measures,/GB7231-2003已由GB2894-2025全部代替/u);
  assert.match(h.conditions,/只核明示标志存在性/u);assert.ok(review('hazards',h.id).remainingUnsupportedBranches.length>0);
});

test('caster GB18831 reference is a conditional defect, not a positive compliance sentence',()=>{
  const h=entity('hazards','H_GBT47236_4_2_3_2_1_1');assert.match(h.description,/已另行确认GB\/T18831的适用版本、具体要求及不符合证据时/u);assert.match(h.description,/选择或设计不符合/u);assert.doesNotMatch(h.measures,/整改。）。|应符合GB\/T18831的规定/u);
});

test('all 118 final dispositions distinguish source gaps from scope and site predicates',()=>{
  assert.equal(report.finalCandidateDispositions.length,118);
  assert.equal(new Set(report.finalCandidateDispositions.map(x=>x.hazardId)).size,118);
  for(const x of report.finalCandidateDispositions){
    assert.ok(x.initialDisposition);assert.ok(x.finalDisposition);
    for(const k of ['remainingUnsupportedBranches','invalidClaimExcluded','scopeExclusions','siteVerificationConditions'])assert.ok(Array.isArray(x[k]),`${x.hazardId}:${k}`);
  }
  assert.equal(report.finalCandidateCounts['已实修'],43);assert.equal(report.finalCandidateCounts['严格已覆盖'],4);
  const forklift=report.finalCandidateDispositions.find(x=>x.hazardId==='H_COM_FORKLIFT_INFO_VERIFY');assert.deepEqual(forklift.remainingUnsupportedBranches,[]);assert.ok(forklift.siteVerificationConditions.length);
  const generic=report.finalCandidateDispositions.find(x=>x.hazardId==='H_GB12801_5_4_6_2');assert.deepEqual(generic.remainingUnsupportedBranches,[]);assert.ok(generic.siteVerificationConditions.length);
});

test('shared hazchem article5 repairs only original branches and keeps regulation identity',()=>{
  const h=entity('hazards','H_66B2A0967E8B4E4BAD7749DF_1');assert.equal(h.lifecycle,'active');assert.match(h.description,/已确认.*具体适用法律/u);assert.match(h.description,/安全条件/u);
  assert.doesNotMatch(h.description,/资格岗位|工伤保险|劳动防护用品/u);
  const k=entity('links','K_ALL_EQUIPMENT_HAZCHEM_SAFETY_CONDITIONS_20261005');assert.equal(k.clauseId,'C_ALL_HAZCHEM_LAW_5');
  const canonical=entity('hazards','H_F3E7D18DBD77459B983AB5CD06');assert.match(canonical.description,/岗位安全责任制度/u);
  assert.equal(entity('clauses','C_66B2A0967E8B4E4BAD7749DF').lawVersionId,'LV_HAZCHEM_REG');
  assert.match(entity('links','K_fb03012279815a93d9c99124').applicability,/仅适用于生产经营单位/u);
  const r=report.finalCandidateDispositions.find(x=>x.hazardId===h.id);assert.equal(r.finalDisposition,'已实修');assert.ok(r.remainingUnsupportedBranches.length>0);
});

test('every link of every authored hazard has current hashes, including historical pending links',()=>{
  const hazards = new Set(report.authoredFiles.filter(p=>p.startsWith('knowledge/hazards/')).map(p=>p.split('/').at(-1).replace(/\.json$/u,'')));
  let checked=0;
  for(const name of fs.readdirSync(new URL('knowledge/links/',root)).filter(x=>x.endsWith('.json'))){
    const l=read(`knowledge/links/${name}`);if(!hazards.has(l.hazardId))continue;
    const rv=review('links',l.id);assert.equal(rv.reviewedContentHash,hash(l),l.id);
    assert.equal(rv.contextHashes.hazard,hash(entity('hazards',l.hazardId)),l.id);
    assert.equal(rv.contextHashes.clause,hash(entity('clauses',l.clauseId)),l.id);checked++;
  }
  assert.ok(checked>=hazards.size);
});

test('old hazchem candidate K remains pending and exact original review bytes are preserved',()=>{
  const id='K_XLSX_NEW14_C3B79F3ED9952CE724957201';const k=entity('links',id);const rv=review('links',id);
  assert.equal(k.lifecycle,'proposed');assert.equal(k.status,'needs_review');assert.equal(rv.decision,'pending');
  assert.equal(k.clauseId,'C_XLSX_WEB_CD13F8489C6C2D427C23098E');assert.match(rv.reason,/不随H准入恢复/u);
  assert.equal(rv.previousReview.decision,'pending');
  for(const group of ['links','reviews/links']){
    const b=report.beforeFiles[`knowledge/${group}/${id}.json`];assert.equal(b.existed,true);
    assert.equal(crypto.createHash('sha256').update(b.fileTextUtf8).digest('hex'),b.sha256);
    assert.deepEqual(JSON.parse(b.fileTextUtf8),group==='links'?rv.previousDefinition:rv.previousReview);
  }
});
