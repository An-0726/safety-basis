'use strict';
const SHELL = 'safety-basis-shell-v15';
const SHELL_FILES = ['./', './index.html', './library.html', './style.css', './library.css', './stage3.css', './app.js',
  './js/field-profiles.js', './js/store.js', './js/search.js', './js/search-vocabulary.js', './js/browse-groups.js', './js/search-guidance.js', './js/field-query-guidance.js', './js/library.js', './js/fulltext-search.js', './js/verified-files.js',
  './manifest.webmanifest', './icon.svg'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL).then(cache => cache.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
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
  if (SHELL_FILES.some(file => new URL(file, self.registration.scope).pathname === url.pathname)) {
    event.respondWith(shell(request));
  }
});
async function shell(request) {
  const cache = await caches.open(SHELL);
  try {
    // no-cache: 每次向服务器确认是否有新版本，不直接用浏览器里还没过期的旧副本。
    const response = await fetch(request, {cache: 'no-cache'});
    if (response.ok) await cache.put(request, response.clone());
    return response;
  } catch {
    return await cache.match(request) || Response.error();
  }
}
