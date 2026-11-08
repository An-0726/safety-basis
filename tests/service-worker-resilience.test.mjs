import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function worker({fetcher,caches}={}) {
  const listeners=new Map(),tasks=[];
  let activated=0;
  const source=fs.readFileSync(new URL('../web/sw.js',import.meta.url),'utf8').replaceAll('__SAFETY_BASIS_DATA_VERSION__','release-new');
  vm.runInNewContext(source,{
    self:{location:{origin:'https://example.test'},registration:{scope:'https://example.test/safety-basis/'},
      addEventListener:(name,handler)=>listeners.set(name,handler),skipWaiting:async()=>{activated++;}},
    caches,fetch:fetcher,URL,Response,AbortController,
    // Preserve deadline behavior without making outage tests wait 12 seconds.
    setTimeout:(fn,ms)=>setTimeout(fn,Math.min(ms,20)),clearTimeout,
  });
  return {listeners,tasks,get activated(){return activated;},request(path){
    let result;
    listeners.get('fetch')({request:new Request(`https://example.test/safety-basis/${path}`),
      respondWith:promise=>{result=promise;},waitUntil:promise=>tasks.push(promise)});
    return result;
  }};
}

test('fresh network modules load even when cache storage never opens',async()=>{
  const w=worker({fetcher:async()=>new Response('export const ok = true;'),caches:{open:()=>new Promise(()=>{})}});
  const response=await w.request('js/new-runtime-module.js?v=release-new');
  assert.equal(await response.text(),'export const ok = true;');
  await Promise.all(w.tasks);
});

test('a hung module body times out and can recover the exact requested cached version',async()=>{
  let matched;
  const w=worker({fetcher:async()=>({ok:true,status:200,statusText:'OK',headers:new Headers(),arrayBuffer:()=>new Promise(()=>{})}),
    caches:{open:async()=>({match:async(request,options)=>{
      matched={url:request.url,ignoreSearch:options.ignoreSearch};return new Response('cached current module');
    }})}});
  const response=await w.request('js/search.js?v=release-new');
  assert.equal(await response.text(),'cached current module');
  assert.equal(matched.ignoreSearch,false);
  assert.match(matched.url,/v=release-new$/);
});

test('offline fallback never exchanges one release query string for another',async()=>{
  const stored=new Map([['https://example.test/safety-basis/js/search.js?v=release-old',new Response('stale module')]]);
  const w=worker({fetcher:async()=>{throw new TypeError('offline');},
    caches:{open:async()=>({match:async request=>stored.get(request.url)?.clone()})}});
  const response=await w.request('js/search.js?v=release-new');
  assert.equal(response.type,'error');
});

test('legal data and release manifests do not fall back to the shell cache',async()=>{
  let cacheReads=0;
  const w=worker({fetcher:async()=>{throw new TypeError('offline');},caches:{open:async()=>{cacheReads++;return {};}}});
  await assert.rejects(w.request('data/search-index.json?sha=old'),/offline/);
  await assert.rejects(w.request('site-manifest.json'),/offline/);
  assert.equal(cacheReads,0);
});

test('an unavailable shell asset does not keep the worker installation pending',async()=>{
  const saved=[];
  const w=worker({fetcher:async url=>String(url).includes('library.css')?new Promise(()=>{}):new Response('asset'),
    caches:{open:async()=>({put:async(url)=>{saved.push(url);}})}});
  let install;
  w.listeners.get('install')({waitUntil:promise=>{install=promise;}});
  await install;
  assert.equal(w.activated,1);
  assert.ok(saved.some(url=>url.endsWith('/js/search-boundaries.js?v=release-new')));
  assert.ok(saved.some(url=>url.endsWith('/js/normative-content.js?v=release-new')));
  assert.ok(saved.filter(url=>url.endsWith('.html')).every(url=>!url.includes('?v=')));
});
