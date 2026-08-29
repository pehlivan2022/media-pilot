// Service worker minimo, FASE 2 passo 2. Attivo SOLO quando servito via http(s) (pwa.js non lo
// registra affatto su file://). Cache-first sulla shell statica (CSS/JS), MAI su assets/data/*.json:
// i dati della dashboard devono sempre arrivare freschi dalla rete quando c'e' rete, coerente con
// "niente dati inventati o stantii" del progetto.
var CACHE = 'media-pilot-shell-v1';
var SHELL = ['app.css', 'data.js', 'store.js', 'radar.js', 'ui.js', 'dashboard-config.js', 'header.js', 'embedded-data.js', 'pwa.js'];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); }));
  self.skipWaiting();
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }));
  self.clients.claim();
});

self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET' || e.request.url.indexOf('/assets/data/') !== -1) return;
  e.respondWith(
    caches.match(e.request).then(function (cached) {
      return cached || fetch(e.request).then(function (resp) {
        var copy = resp.clone();
        caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        return resp;
      });
    }).catch(function () { return caches.match(e.request); })
  );
});
