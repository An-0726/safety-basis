'use strict';
const SHELL = 'safety-basis-shell-v17-__SAFETY_BASIS_DATA_VERSION__';
const BUILT_DATA_VERSION = '__SAFETY_BASIS_DATA_VERSION__';
const DATA_VERSION = BUILT_DATA_VERSION.startsWith('__') ? '' : BUILT_DATA_VERSION;
const NETWORK_TIMEOUT_MS = 12000;
const CACHE_TIMEOUT_MS = 1500;
const SHELL_FILES = ['./', './index.html', './library.html', './style.css', './library.css', './stage3.css', './app.js',
  './js/field-profiles.js', './js/store.js', './js/search.js', './js/search-vocabulary.js', './js/browse-groups.js', './js/search-guidance.js', './js/search-boundaries.js', './js/field-query-guidance.js', './js/library.js', './js/fulltext-search.js', './js/verified-files.js', './js/normative-content.js',
  './js/query-intent.js', './js/search-facets.js', './js/bootstrap-watchdog.js',
  './major-criteria.html', './major-criteria.css', './js/major-criteria.js', './js/major-criteria-model.js', './js/major-criteria-reference-model.js', './js/major-criteria-directory-model.js', './js/major-criteria-reading-model.js',
  './manifest.webmanifest', './icon.svg'];
self.addEventListener('install', event => {
  // One unavailable optional shell asset must not strand clients on an older
  // worker. Every prefetched resource is bounded and can be fetched on demand.
  event.waitUntil(precache().then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  // Old controlled pages can reopen their namespace while claim() is pending.
  // Clean again after ownership changes so those late opens do not leave stale caches.
  event.waitUntil(clearPreviousCaches().then(() => self.clients.claim()).then(clearPreviousCaches));
});
function clearPreviousCaches() {
  return caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('safety-basis-') && key !== SHELL)
    .map(key => caches.delete(key))));
}
self.addEventListener('message', event => {
  if(event.data?.type === 'safety-basis:cleanup-shell-caches') event.waitUntil(clearPreviousCaches());
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // Current legal status must never silently fall back to an older cached release.
  if (url.pathname.includes('/data/') || url.pathname.endsWith('/site-manifest.json')) {
    event.respondWith(fetch(request, {cache: 'no-store'}));
    return;
  }
  const scopePath=new URL(self.registration.scope).pathname;
  const modulePath=url.pathname.startsWith(`${scopePath}js/`) && url.pathname.endsWith('.js');
  if (modulePath || SHELL_FILES.some(file => new URL(file, self.registration.scope).pathname === url.pathname)) {
    event.respondWith(shell(request,event));
  }
});

function assetUrl(file) {
  const url=new URL(file,self.registration.scope);
  if(DATA_VERSION && /\.(?:js|css)$/.test(url.pathname)) url.searchParams.set('v',DATA_VERSION);
  return url.href;
}

async function networkShell(request) {
  const controller=new AbortController();
  let timer;
  const deadline=new Promise((_,reject)=>{
    timer=setTimeout(()=>{controller.abort();reject(new Error('页面文件读取超时'));},NETWORK_TIMEOUT_MS);
  });
  const read=(async()=>{
    const response=await fetch(request,{cache:'no-store',signal:controller.signal});
    if(!response.ok) return response;
    // Bound stalled bodies too; a headers-only deadline still leaves an ES
    // module import pending forever and the page stuck on its initial message.
    const bytes=await response.arrayBuffer();
    return new Response(bytes,{status:response.status,statusText:response.statusText,headers:response.headers});
  })();
  try { return await Promise.race([read,deadline]); }
  finally { clearTimeout(timer); }
}

async function boundedCache(operation) {
  let timer;
  const deadline=new Promise((_,reject)=>{
    timer=setTimeout(()=>reject(new Error('离线缓存暂不可用')),CACHE_TIMEOUT_MS);
  });
  try { return await Promise.race([Promise.resolve().then(operation),deadline]); }
  finally { clearTimeout(timer); }
}

async function precache() {
  let cache;
  try { cache=await boundedCache(()=>caches.open(SHELL)); } catch { return; }
  let next=0;
  const worker=async()=>{
    while(next<SHELL_FILES.length) {
      const url=assetUrl(SHELL_FILES[next++]);
      try {
        const response=await networkShell(url);
        if(response.ok) await boundedCache(()=>cache.put(url,response));
      } catch {}
    }
  };
  await Promise.all(Array.from({length:4},worker));
}

async function shell(request,event) {
  try {
    const response = await networkShell(request);
    if (response.ok) {
      const copy=response.clone();
      // Cache storage is optional and is never on the successful network path.
      const save=(async()=>{
        try {
          const cache=await boundedCache(()=>caches.open(SHELL));
          await boundedCache(()=>cache.put(request,copy));
        } catch {}
      })();
      event?.waitUntil(save);
    }
    return response;
  } catch {
    // Keep the exact query string: ?v=old must never fall back to ?v=new.
    // Data and the release manifest never enter this fallback path.
    try {
      const cache=await boundedCache(()=>caches.open(SHELL));
      return await boundedCache(()=>cache.match(request,{ignoreSearch:false})) || Response.error();
    }
    catch { return Response.error(); }
  }
}
