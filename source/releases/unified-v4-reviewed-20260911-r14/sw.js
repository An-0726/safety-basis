'use strict';
const SHELL = 'safety-basis-shell-v4';
const SHELL_FILES = ['./', './index.html', './library.html', './style.css', './library.css', './app.js',
  './js/store.js', './js/search.js', './js/library.js', './js/fulltext-search.js', './js/verified-files.js',
  './manifest.webmanifest', './icon.svg'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(SHELL).then(cache => cache.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('safety-basis-') && key !== SHELL)
    .map(key => caches.delete(key)))).then(() => self.clients.claim()));
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
    const response = await fetch(request);
    if (response.ok) await cache.put(request, response.clone());
    return response;
  } catch {
    return await cache.match(request) || Response.error();
  }
}
