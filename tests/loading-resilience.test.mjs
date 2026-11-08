import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {DataStore} from '../web/js/store.js';
import {VerifiedFiles, loadResource, resolveDataVersion} from '../web/js/verified-files.js';

const never = () => new Promise(() => {});
const sha = text => createHash('sha256').update(text).digest('hex');
const keyOf = url => new URL(url, 'https://example.test/').pathname.slice(1);
const codeIs = code => error => error?.code === code;

test('secondary pages also reject a page and script/data release disagreement',()=>{
  const previous=globalThis.document;
  try{
    globalThis.document={querySelector:()=>({content:'release-page'})};
    assert.equal(resolveDataVersion(),'release-page');
    assert.equal(resolveDataVersion('release-page'),'release-page');
    assert.throws(()=>resolveDataVersion('release-other'),codeIs('VERSION_MISMATCH'));
    globalThis.document={querySelector:()=>null};
    assert.equal(resolveDataVersion(),'','private embeds without public page metadata remain supported');
  }finally{if(previous===undefined)delete globalThis.document;else globalThis.document=previous;}
});

function fixture({version='test-release', count=2, mutateProfiles}={}) {
  const asOf='2026-11-08', releaseHash='a'.repeat(64);
  const clauses=[], hazards=[], profiles=[], index=[];
  for(let n=1;n<=count;n++) {
    const ref={linkId:`K${n}`,clauseId:`C${n}`,clauseShard:'c0',role:'direct',applicability:'仅限软件合成示例',jurisdictionCode:'CN'};
    const hazard={id:`H${n}`,title:`测试设备${n}条目`,conditions:'示例条件',status:'已核验',publishable:true,basisRefs:[ref]};
    hazards.push(hazard);
    clauses.push({id:`C${n}`,lawId:'LV1',status:'现行有效',quote:'合成条文，仅用于软件测试。'});
    index.push({id:hazard.id,title:hazard.title,status:'已核验',publishable:true,shard:'h0',searchText:hazard.title});
    profiles.push({schemaVersion:1,id:`FPR_${n}`,revision:1,hazardId:hazard.id,title:`测试核查场景${n}`,
      inspectionClass:'core_onsite_inspection',defaultFieldEntry:'conditional',contentDisposition:'onsite_finding',
      applicability:{requires:['示例适用条件'],excludes:['不代表真实法源'],perUseFacts:['applicableRequirementConfirmed','siteTriggerConfirmed','defectObserved']},
      evidenceRequirements:['合成证据'],correctiveDirection:'合成整改方向',findingTemplate:{text:'{{place}}处的合成问题',slots:[{key:'place',label:'位置'}]},
      basisLinkIds:[ref.linkId],recordKind:'reusable_field_profile',observedViolation:false,
      sourceHazard:{id:hazard.id,title:hazard.title,conditions:hazard.conditions},
      bases:[{linkId:ref.linkId,clauseId:ref.clauseId,role:ref.role,applicability:ref.applicability,jurisdictionCode:'CN',lawVersionId:'LV1',lawId:'L1',lawJurisdictionCode:'CN'}]});
  }
  mutateProfiles?.(profiles);
  const data={
    'data/manifest.json':{schemaVersion:2,dataVersion:version,releaseHash,
      hazardShards:[{id:'h0',url:'data/hazards/h0.json'}],clauseShards:[{id:'c0',url:'data/clauses/c0.json'}],
      files:{searchIndex:'data/search-index.json',lawIndex:'data/law-index.json',taxonomy:'data/taxonomy.json',fieldProfiles:'data/field-profiles.json'},
      counts:{hazards:count,laws:1,clauses:count,links:count,fieldProfiles:count}},
    'data/search-index.json':index,
    'data/law-index.json':[{id:'LV1',name:'合成法源',status:'现行有效',effectiveDate:'2025-01-01',sourceUrl:'https://example.gov.cn/test',clauseCount:count,clauseRefs:clauses.map(c=>({clauseId:c.id,clauseShard:'c0'}))}],
    'data/taxonomy.json':{},
    'data/field-profiles.json':{schemaVersion:1,asOf,records:profiles},
    'data/hazards/h0.json':{records:hazards},
    'data/clauses/c0.json':{records:clauses},
  };
  const bytes=new Map(Object.entries(data).map(([path,value])=>[path,JSON.stringify(value)]));
  const manifest={schemaVersion:'safety-site-bundle-v1',asOf,dataVersion:version,releaseHash,
    fileHashes:Object.fromEntries([...bytes].map(([path,body])=>[path,sha(body)]))};
  bytes.set('site-manifest.json',JSON.stringify(manifest));
  return {bytes,manifest,data,response:path=>bytes.has(path)?new Response(bytes.get(path)):new Response('',{status:404})};
}

test('a fetch that ignores abort still times out, retries once, and exposes the failed resource',async()=>{
  const signals=[],retries=[];
  const files=new VerifiedFiles('.', {timeoutMs:15,retries:1,
    fetcher:(_url,options)=>{signals.push(options.signal);return never();},onRetry:info=>retries.push(info)});
  await assert.rejects(files.init({required:true}),error=>error.code==='TIMEOUT'&&error.resource==='发布清单');
  assert.equal(signals.length,2);
  assert.ok(signals.every(signal=>signal.aborted));
  assert.equal(retries.length,1);
  assert.equal(files.manifest,null);
});

test('the deadline includes a body that never finishes, not just response headers',async()=>{
  await assert.rejects(loadResource('https://example.test/slow.json',{
    timeoutMs:15,retries:0,fetcher:async()=>({ok:true,status:200,json:never}),
  }),codeIs('TIMEOUT'));
  const f=fixture(),files=new VerifiedFiles('.', {timeoutMs:15,retries:0,
    fetcher:async url=>keyOf(url)==='site-manifest.json'?f.response('site-manifest.json'):{ok:true,status:200,arrayBuffer:never}});
  await files.init({required:true});
  await assert.rejects(files.read('data/search-index.json'),codeIs('TIMEOUT'));
  assert.equal(files.pending.size,0);
});

test('one transient transport failure recovers; a missing or malformed resource is not retried indefinitely',async()=>{
  let calls=0;
  assert.deepEqual(await loadResource('example',{fetcher:async()=>{
    if(++calls===1) throw new TypeError('connection reset');
    return new Response('{"ready":true}');
  }}),{ready:true});
  assert.equal(calls,2);
  calls=0;
  await assert.rejects(loadResource('example',{fetcher:async()=>{calls++;return new Response('',{status:404});}}),codeIs('HTTP'));
  assert.equal(calls,1);
  calls=0;
  await assert.rejects(loadResource('example',{fetcher:async()=>{calls++;return new Response('<html>gateway</html>');}}),codeIs('FORMAT'));
  assert.equal(calls,1);
});

test('an explicit cancellation aborts without automatic retry',async()=>{
  let calls=0;
  const controller=new AbortController();
  const loading=loadResource('example',{signal:controller.signal,timeoutMs:1000,fetcher:()=>{calls++;return never();}});
  controller.abort();
  await assert.rejects(loading,codeIs('CANCELLED'));
  assert.equal(calls,1);
});

test('concurrent verified reads share a request; later corrupt bytes are rejected without integrity retries',async()=>{
  const f=fixture();let calls=0,corrupt=false;
  const files=new VerifiedFiles('.',{fetcher:async url=>{
    const key=keyOf(url);
    if(key==='data/search-index.json') {calls++;if(corrupt)return new Response('[]');}
    return f.response(key);
  }});
  await files.init({required:true});
  const rows=await Promise.all([files.read('data/search-index.json'),files.read('data/search-index.json')]);
  assert.equal(calls,1);assert.deepEqual(rows[0],rows[1]);
  corrupt=true;
  await assert.rejects(files.read('data/search-index.json'),codeIs('INTEGRITY'));
  assert.equal(calls,2);
});

test('page version, release version and data version must agree',async()=>{
  const f=fixture({version:'new-release'});
  let count=0;
  const store=new DataStore('.',{fetcher:async url=>{count++;return f.response(keyOf(url));}});
  await assert.rejects(store.init({expectedVersion:'old-release',requiredManifest:true}),codeIs('VERSION_MISMATCH'));
  assert.equal(count,1);
  assert.equal(store.searchIndex.length,0);
  f.manifest.dataVersion='other-release';
  f.bytes.set('site-manifest.json',JSON.stringify(f.manifest));
  await assert.rejects(store.init({requiredManifest:true}),codeIs('VERSION_MISMATCH'));
  assert.equal(store.searchIndex.length,0);
});

test('core search is usable while profile loading stalls; profile retry restores only fully validated joins',async()=>{
  const f=fixture();let blocked=true;
  const phases=[];
  const store=new DataStore('.',{timeoutMs:20,retries:0,fetcher:async url=>{
    const key=keyOf(url);
    if(key==='data/field-profiles.json'&&blocked)return never();
    return f.response(key);
  }});
  await store.init({deferFieldProfiles:true,requiredManifest:true,onProgress:info=>phases.push(info.phase)});
  assert.equal(store.searchIndex.length,2);
  assert.equal(store.fieldProfileStatus,'loading');
  assert.equal(store.getFieldProfiles('H1').length,0);
  assert.ok(phases.indexOf('core-ready')<phases.indexOf('profiles'));
  await store.fieldProfilesReady;
  assert.equal(store.fieldProfileStatus,'unavailable');
  assert.equal(store.fieldProfileError.code,'TIMEOUT');
  assert.match(store.fieldProfileNotice,/超时/);
  assert.equal(store.searchIndex.length,2);
  blocked=false;
  await store.loadFieldProfiles();
  assert.equal(store.fieldProfileStatus,'ready');
  assert.equal(store.fieldProfileNotice,'');
  assert.equal(store.getFieldProfiles('H1').length,1);
  const text=store.searchIndex[0].searchText;
  await store.loadFieldProfiles();
  assert.equal(store.searchIndex[0].searchText,text,'retry must not duplicate indexed profile titles');
});

test('parallel profile validation shares hazard and clause shard requests',async()=>{
  const f=fixture({count:6}),requests=new Map();
  const store=new DataStore('.',{fetcher:async url=>{
    const key=keyOf(url);requests.set(key,(requests.get(key)||0)+1);return f.response(key);
  }});
  await store.init({requiredManifest:true});
  assert.equal(store.fieldProfileStatus,'ready');
  assert.equal(store.fieldProfiles.size,6);
  assert.equal(requests.get('data/hazards/h0.json'),1);
  assert.equal(requests.get('data/clauses/c0.json'),1);
  assert.deepEqual((await store.getLawDetail(store.lawIndex[0])).clauses.map(row=>row.clause.id),['C1','C2','C3','C4','C5','C6']);
});

test('one invalid profile join prevents every profile from being admitted, without hiding the basic index',async()=>{
  const f=fixture({mutateProfiles:profiles=>{profiles[1].bases[0].applicability='incorrect scope';}});
  const store=await new DataStore('.',{fetcher:async url=>f.response(keyOf(url))}).init({requiredManifest:true});
  assert.equal(store.fieldProfileStatus,'unavailable');
  assert.equal(store.fieldProfiles.size,0);
  assert.equal(store.searchIndex.length,2);
  assert.ok(store.searchIndex.every(row=>row.fieldProfiles.length===0));
});

test('retrying initialization after a failed index request clears the failure and reloads the same store',async()=>{
  const f=fixture();let fail=true;
  const store=new DataStore('.',{retries:0,fetcher:async url=>{
    const key=keyOf(url);
    if(fail&&key==='data/search-index.json')throw new TypeError('offline');
    return f.response(key);
  }});
  await assert.rejects(store.init({requiredManifest:true}),codeIs('NETWORK'));
  assert.equal(store.searchIndex.length,0);
  fail=false;
  await store.init({requiredManifest:true});
  assert.equal(store.searchIndex.length,2);
  assert.equal(store.loadingState.phase,'ready');
});

test('a cancelled older initialization cannot overwrite a newer release after a late response',async()=>{
  const older=fixture({version:'older',count:1}),newer=fixture({version:'newer',count:3});
  let current=older,releaseOld,markStarted;
  const started=new Promise(resolve=>{markStarted=resolve;});
  const delayed=new Promise(resolve=>{releaseOld=resolve;});
  const store=new DataStore('.',{retries:0,fetcher:async url=>{
    const key=keyOf(url);
    if(current===older&&key==='data/manifest.json'){markStarted();return delayed;}
    return current.response(key);
  }});
  const pending=store.init({requiredManifest:true});
  const rejected=assert.rejects(pending,codeIs('CANCELLED'));
  await started;
  current=newer;
  await store.init({requiredManifest:true});
  releaseOld(older.response('data/manifest.json'));
  await rejected;
  assert.equal(store.manifest.dataVersion,'newer');
  assert.equal(store.searchIndex.length,3);
});
