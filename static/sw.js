// Wild4Life Service Worker
const CACHE = 'w4l-v2';
const OFFLINE_URL = '/';

// Only pre-cache genuine static assets — never HTML pages.
// HTML pages are dynamic (blog posts, donation counts) so they must always
// be fetched fresh from the network.
const PRECACHE = [
  '/static/site/css/main.css',
  '/static/css/site-overrides.css',
  '/static/site/js/main.js',
  '/static/site/vendor/bootstrap/css/bootstrap.min.css',
  '/static/site/vendor/bootstrap/js/bootstrap.bundle.min.js',
  '/static/site/img/wild.jpg',
  '/static/site/img/favicon.jpg',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('/dashboard/')) return;
  if (e.request.url.includes('/admin/'))    return;
  if (e.request.url.includes('/api/'))      return;

  const url = new URL(e.request.url);

  // HTML pages — always network-first so new blog posts, donations, etc.
  // are always up to date. Fall back to cache only when offline.
  if (e.request.headers.get('accept') && e.request.headers.get('accept').includes('text/html')) {
    e.respondWith(
      fetch(e.request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE).then((c) => c.put(e.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(e.request).then((cached) => cached || caches.match(OFFLINE_URL)))
    );
    return;
  }

  // Static assets (CSS, JS, images) — cache-first for speed.
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request)
        .then((response) => {
          if (response.ok && url.origin === self.location.origin) {
            const clone = response.clone();
            caches.open(CACHE).then((c) => c.put(e.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(OFFLINE_URL));
    })
  );
});
