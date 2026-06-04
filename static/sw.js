// Wild4Life Service Worker
const CACHE = 'w4l-v1';
const OFFLINE_URL = '/';

const PRECACHE = [
  '/',
  '/donate/',
  '/blog/',
  '/about/',
  '/contact/',
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
  if (e.request.url.includes('/dashboard/')) return; // never cache dashboard
  if (e.request.url.includes('/admin/'))    return;
  if (e.request.url.includes('/api/'))      return;

  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request)
        .then((response) => {
          if (response.ok && e.request.url.startsWith(self.location.origin)) {
            const clone = response.clone();
            caches.open(CACHE).then((c) => c.put(e.request, clone));
          }
          return response;
        })
        .catch(() => caches.match(OFFLINE_URL));
    })
  );
});
