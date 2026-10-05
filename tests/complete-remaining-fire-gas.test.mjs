import fs from 'node:fs';
import crypto from 'node:crypto';
import test from 'node:test';
import assert from 'node:assert/strict';
import {normativeContentText,renderNormativeContent} from '../web/js/normative-content.js';
const root=new URL('../',import.meta.url);
const file=p=>fs.readFileSync(new URL(p,root));
const data=p=>JSON.parse(file(p));
const entity=(g,id)=>data(`knowledge/${g}/${id}.json`);
const report=data('docs/COMPLETE_REMAINING_FIRE_GAS_AUTHOR_20261005.json');
const text=h=>[h.title,h.description,h.conditions,h.measures].join('\n');
function canonical(x){if(Array.isArray(x))return x.map(canonical);if(x&&typeof x==='object')return Object.fromEntries(Object.keys(x).filter(k=>k!=='canonicalHash').sort().map(k=>[k,['aliases','places','keywords'].includes(k)&&Array.isArray(x[k])?[...x[k]].sort():canonical(x[k])]));return x;}
const hash=x=>crypto.createHash('sha256').update(JSON.stringify(canonical(x))).digest('hex');

test('original 41 have nine bounded repairs and 32 unchanged dispositions, with dependencies separate',()=>{
 const original=report.decisions.filter(d=>d.scope==='original_41');
 assert.equal(original.length,9);assert.equal(report.unchangedDispositions.length,32);
 assert.equal(new Set([...original,...report.unchangedDispositions].map(d=>d.hazardId)).size,41);
 assert.equal(report.decisions.filter(d=>d.scope==='additional_source_dependency').length,6);
 for(const d of [...report.decisions,...report.unchangedDispositions]){assert.ok(Array.isArray(d.remainingUnsupportedBranches));assert.ok(Array.isArray(d.invalidClaimExcluded));}
 for(const [path,sha] of Object.entries(report.unchangedFileSha256))assert.equal(crypto.createHash('sha256').update(file(path)).digest('hex'),sha,path);
});
test('current bounded hazard and link reviews are exact and retain historical review fingerprints',()=>{
 for(const d of report.decisions){
  const h=entity('hazards',d.hazardId),hr=entity('reviews/hazards',d.hazardId);
  assert.equal(hr.reviewedContentHash,hash(h));
  const prior=report.beforeFileHashes[`knowledge/reviews/hazards/${d.hazardId}.json`];
  if(prior.existed){assert.match(hr.previousReviewFileSha256,/^[a-f0-9]{64}$/);assert.equal(hr.previousReviewFileSha256,prior.sha256);assert.ok(hr.previousReview);}else{assert.equal(hr.previousReview,undefined);}
  assert.ok(hr.previousDefinition);
  assert.equal(hr.decision,d.action==='quarantine_unsupported_dependency'?'pending':'verified');
  for(const id of d.linkIds){const k=entity('links',id),r=entity('reviews/links',id);assert.equal(r.reviewedContentHash,hash(k));assert.equal(r.contextHashes.hazard,hash(h));assert.equal(r.contextHashes.clause,hash(entity('clauses',k.clauseId)));}
 }
});
test('warehouse rules retain existing-storage scope, exclusions and measured branches',()=>{
 for(const id of ['H069','H_21A69E2CA823BC59272F464D','H_45A066D644BE4A0992ECC95E1B','H_B16CF9FD47A6467189A9B9BC52']){const h=entity('hazards',id);assert.match(h.conditions,/既有仓储/);assert.match(h.conditions,/炸药仓库、花炮仓库/);}
 assert.match(text(entity('hazards','H069')),/0\.3m/);assert.match(text(entity('hazards','H069')),/从横梁算起/);
 assert.equal(entity('links','K_XLSX_WEB_03B2F837CD3D64D61AB79B20').clauseId,'C_XF1131_6_8');
 assert.equal(entity('clauses','C_XF1131_3_4_P2').quote,'仓储场所应划线标明库房的墙距、垛距、主要通道、货物固定位置等，并按本标准要求设置必要的防火安全标志。');
});
test('fan duplicate remains isolated with exact conditional canonical',()=>{
 const h=entity('hazards','H_0BE49AFFA4884C639EE50FD565');assert.equal(h.lifecycle,'proposed');
 const r=report.unchangedDispositions.find(d=>d.hazardId===h.id);assert.equal(r.conditionalCanonical,'H038');
 assert.equal(entity('links','K_AC0819521C0C6C9961FDEB').clauseId,'C_HJ2000_5_4_1');
});
test('manual alarm signs are wall-mounted design branch; hydrant position does not import draft preference',()=>{
 const h=entity('hazards','H_99B75F33D550486BBA89A77139');assert.match(h.conditions,/壁挂/);assert.match(h.conditions,/设计/);assert.match(h.conditions,/火药、炸药、弹药、火工品/);assert.doesNotMatch(h.description,/遮挡|柜子/);
 const c=entity('clauses','C_GB50116_6_3_2');assert.match(c.quote,/宜为1.3m～1.5m/);
 const f=entity('hazards','H_524210530E054FE1BB1D918820');assert.doesNotMatch(text(f),/优先|首先|疏散门外/);assert.match(f.description,/方便使用或维护/);
});
test('fire supply keeps third-level exception and complete 13-row table with exact fallback',()=>{
 const c=entity('clauses','C_GB55037_10_1_5'),t=c.contentParts[1];assert.equal(t.bodyRows.length,13);assert.equal(t.columnCount,3);
 assert.equal(c.quote,normativeContentText(c.contentParts));assert.match(c.quote,/除三级消防用电负荷外/);assert.match(c.quote,/不大于3000m²/);assert.match(c.quote,/大于100000m³/);
 assert.deepEqual(t.bodyRows.map(r=>r.at(-1).text),['3.0','2.0','3.0','2.0','3.0','2.0','2.0','1.0','1.0','2.0','3.0','2.0','2.0']);
 assert.deepEqual(entity('reviews/clauses',c.id).reviewedTableIds,['T_GB55037_10_1_5']);
 assert.match(renderNormativeContent(c),/rowspan="2"/);assert.match(renderNormativeContent(c),/59/);
 const h=entity('hazards','H_66611E63B2814335BFA0EF5E0D');assert.match(h.conditions,/除三级消防用电负荷外/);assert.doesNotMatch(text(h),/柴油|30s|30秒|设置于消防泵房/);
});
test('JGJ91 evidence and complete text correct the exact historical defects',()=>{
 const e=entity('evidence','E_MOHURD_JGJ91_2019');assert.match(e.locator,/211/);assert.match(e.previousEvidence.locator,/307/);assert.match(e.sourceClass,/university-hosted/);assert.match(e.snapshotSha256,/^[a-f0-9]{64}$/);
 assert.equal(entity('clauses','C_JGJ91_5_3_3').quote,'使用强酸、强碱等有化学品危险隐患的实验室，应就近设置应急洗眼器及应急喷淋。');
 assert.match(entity('clauses','C_JGJ91_5_2_1').quote,/GB 13690的规定。$/);
 for(const id of ['H077','H_3C5449E0928B4B219D77694FDC','H_060514A9AB6347C6A98CD93842','H_387CD4000D844D269A439E4D45','H_C706DAF977FA4CC5960E97DD05'])assert.match(entity('hazards',id).conditions,/新建、扩建、改建科研建筑的设计/);
});
test('unsupported laboratory compound is retained and isolated; five existing links individually reviewed',()=>{
 const h=entity('hazards','H_A4AF26421A0E404F82BF740A6D');assert.equal(h.lifecycle,'proposed');assert.equal(h.mode,'candidate');assert.equal(h.mergedInto,null);
 const k=entity('links','K_XLSX_WEB_'+h.id);assert.equal(k.lifecycle,'proposed');assert.equal(entity('reviews/links',k.id).decision,'pending');
 const jgj=report.dependencyGateBefore.filter(r=>r.link.hazardId!=='H038');assert.equal(jgj.length,5);for(const r of jgj)assert.equal(r.linkGate.ok,true);
 const a=entity('hazards','H_3C5449E0928B4B219D77694FDC'),b=entity('hazards','H_060514A9AB6347C6A98CD93842');assert.match(a.conditions,/第一句/);assert.match(b.conditions,/第二句/);
});
test('mechanical pressure interlock branch does not merge flame protection or other industries',()=>{
 const h=entity('hazards','H_CF_MAJOR_06');assert.match(h.title,/机械企业/);assert.match(h.conditions,/煤气或天然气/);assert.match(h.conditions,/前两个“或者”分支/);assert.doesNotMatch(h.description,/等可燃气体|火焰|熄火/);
 assert.equal(entity('links','K_CF_MAJOR_06_C_PDDB_7').clauseId,'C_PDDB_7');assert.equal(report.majorTopicChangeRecommendation.judgmentItemCountChange,0);
});
test('author file boundary excludes shared deployment controls and original source files',()=>{
 assert.equal(new Set(report.authoredFiles).size,report.authoredFiles.length);
 for(const p of report.authoredFiles){assert.ok(fs.existsSync(new URL(p,root)),p);assert.doesNotMatch(p,/knowledge\/manifest|source\/publication|PROJECT_STATE|\.github\/|major-criteria.*catalog|\.pdf$|\.docx$/);}
});

test('canonical fan definition and both links are closed without releasing unsupported fallback',()=>{
 const h=entity('hazards','H038');assert.match(h.conditions,/仅适用于大气污染治理工程/);assert.match(h.measures,/宜选择叶轮防爆而电机不防爆/);assert.match(h.conditions,/指导使用/);
 const k=entity('links','K_24829595e4a1c7c20086ebe0'),r=entity('reviews/links',k.id);assert.equal(k.lifecycle,'proposed');assert.equal(r.decision,'pending');assert.equal(r.contextHashes.hazard,hash(h));
});

test('one missing laboratory safety facility or system suffices for each corrected branch',()=>{
 for(const [id,left,right] of [['H077','未就近设置应急洗眼器','未就近设置应急喷淋'],['H_387CD4000D844D269A439E4D45','未设置监测报警系统','未设置自动灭火系统']]){
  const h=entity('hazards',id);assert.ok(h.description.includes(left+'，或者'+right));assert.match(h.description,/任一.*缺失/);
  const result=report.decisions.find(d=>d.hazardId===id);assert.match(result.positiveCase,/仅缺.*或仅缺.*分别触发/);
 }
});
