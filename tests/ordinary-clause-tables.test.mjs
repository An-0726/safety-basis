import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';
import assert from 'node:assert/strict';
import {DataStore} from '../web/js/store.js';
import {renderNormativeContent,normativeContentText} from '../web/js/normative-content.js';
const original=JSON.parse(fs.readFileSync(new URL('../knowledge/clauses/C_12158_4_2_3_4.json',import.meta.url),'utf8'));
const clause=()=>({...structuredClone(original),article:'第4.2.3.4条',checked:'2026-10-04',status:'现行有效'});
const source=fs.readFileSync(new URL('../web/app.js',import.meta.url),'utf8').replace(/^import[^\n]*\n/gm,'').replace(/^export /gm,'').replace("if(typeof document!=='undefined') boot();",'')+'\n state.store={manifest:{dataVersion:"test"},verifiedFiles:{manifest:{}}}; globalThis.testApi={basisHtml,lawClauseHtml,hazardText,hazardFullText,lawText};';
const context={renderNormativeContent};vm.createContext(context);new vm.Script(source).runInContext(context);
const api=context.testApi;
const law={id:'L1',name:'测试标准',level:'国家标准',scope:'全国',status:'现行有效'};
const basis=c=>({ref:{linkId:'K1',role:'direct',applicability:'限实际环境分支；保留工艺需要例外'},clause:c,law,sourceUrl:'https://example.gov.cn'});

test('ordinary hazard and law render all nine rows, spans, source note and exception',()=>{
 const c=clause();for(const html of [api.basisHtml(basis(c)),api.lawClauseHtml({hazardIds:[]},c)]){
  assert.equal((html.match(/<tr>/g)||[]).length,10);
  assert.match(html,/rowspan="4"/);assert.match(html,/colspan="2"/);
  assert.match(html,/工艺需要/);assert.match(html,/必要时/);assert.match(html,/2区/);
  assert.match(html,/GB\/T 3836.11/);assert.match(html,/role="region" tabindex="0"/);
  assert.match(html,/原PDF第 11 页/);
 }
});
test('ordinary hazard and law copies preserve the complete fallback without HTML',()=>{
 const c=clause(), h={id:'H1',title:'受限定义',description:'描述',conditions:'条件',measures:'整改'};
 for(const output of [api.hazardText(h,[basis(c)]),api.hazardFullText(h,[basis(c)]),api.lawText({law,clauses:[{clause:c}]})]){
  assert.ok(output.includes(c.quote));assert.ok(output.includes('2区\tⅠ类\t3.0\t100'));assert.doesNotMatch(output,/<table/);
 }
});
test('ordinary load rejects malformed rich tables before caching and accepts legacy plain clauses',async()=>{
 for(const mutate of [c=>c.quote='short',c=>c.contentParts=null,c=>c.contentParts[1].bodyRows[0][0].rawHtml='<img>']){
  const c=clause();mutate(c);const store=new DataStore();store.clauseShardUrls.set('c0','unused');store.fetchJson=async()=>({records:[c]});
  await assert.rejects(store.loadClauseShard('c0'));assert.equal(store.clauseCache.size,0);
 }
 const store=new DataStore();store.clauseShardUrls.set('c0','unused');store.fetchJson=async()=>({records:[{id:'C_PLAIN',quote:'全文'}]});assert.equal((await store.loadClauseShard('c0')).get('C_PLAIN').quote,'全文');
});
test('table cells and captions escape HTML instead of accepting markup',()=>{
 const c=clause();c.contentParts[1].caption='<script>x</script>';c.contentParts[1].bodyRows[0][1].text='<img onerror=x>';c.quote=normativeContentText(c.contentParts);
 const html=api.basisHtml(basis(c));assert.doesNotMatch(html,/<script>|<img /);assert.match(html,/&lt;img onerror=x&gt;/);
});
