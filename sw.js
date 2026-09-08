'use strict';
const SHELL='safety-basis-shell-v2';
const DATA='safety-basis-data-v2';
const SHELL_FILES=['./','./index.html','./style.css','./app.js','./js/store.js','./js/search.js','./manifest.webmanifest','./icon.svg'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(SHELL).then(c=>c.addAll(SHELL_FILES)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('safety-basis-')&&!([SHELL,DATA].includes(k))).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',event=>{
  const req=event.request;if(req.method!=='GET')return;
  const url=new URL(req.url);if(url.origin!==self.location.origin)return;
  if(url.pathname.includes('/data/')){event.respondWith(networkFirst(req,DATA));return}
  event.respondWith(staleWhileRevalidate(req,SHELL));
});
async function networkFirst(req,cacheName){const cache=await caches.open(cacheName);try{const res=await fetch(req);if(res.ok)cache.put(req,res.clone());return res}catch{const cached=await cache.match(req);if(cached)return cached;throw new Error('offline')}}
async function staleWhileRevalidate(req,cacheName){const cache=await caches.open(cacheName);const cached=await cache.match(req);const net=fetch(req).then(res=>{if(res.ok)cache.put(req,res.clone());return res}).catch(()=>null);return cached||await net||Response.error()}
