// DAR AL CODE - Service Worker for PWA & Push Notifications
// Uses Web Push API with VAPID (Privacy-focused, no Firebase)

const CACHE_NAME = 'dar-alcode-v2';

// Assets to cache for offline support
const ASSETS_TO_CACHE = [
  '/',
  '/icon-192.png',
  '/icon-512.png',
  '/manifest.json'
];

// Install event - cache essential assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching app shell');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests and API calls
  if (event.request.method !== 'GET' || event.request.url.includes('/api/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((response) => {
      if (response) {
        return response;
      }
      return fetch(event.request).then((networkResponse) => {
        if (!networkResponse || networkResponse.status !== 200) {
          return networkResponse;
        }
        const responseToCache = networkResponse.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseToCache);
        });
        return networkResponse;
      });
    }).catch(() => {
      if (event.request.mode === 'navigate') {
        return caches.match('/');
      }
    })
  );
});

// Push notification event - Web Push API
self.addEventListener('push', (event) => {
  console.log('[SW] Push received:', event);

  let notificationData = {
    title: 'دار الكود للاستشارات الهندسية',
    body: 'لديك إشعار جديد',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    tag: 'dar-alcode-notification',
    requireInteraction: true,
    vibrate: [200, 100, 200],
    data: { url: '/' }
  };

  // Parse push data if available
  if (event.data) {
    try {
      const data = event.data.json();
      notificationData = {
        ...notificationData,
        title: data.title_ar || data.title || notificationData.title,
        body: data.body_ar || data.body || data.message_ar || data.message || notificationData.body,
        tag: data.tag || data.id || notificationData.tag,
        data: { url: data.url || data.reference_url || '/' }
      };
    } catch (e) {
      notificationData.body = event.data.text();
    }
  }

  event.waitUntil(
    self.registration.showNotification(notificationData.title, {
      body: notificationData.body,
      icon: notificationData.icon,
      badge: notificationData.badge,
      tag: notificationData.tag,
      requireInteraction: notificationData.requireInteraction,
      vibrate: notificationData.vibrate,
      data: notificationData.data,
      dir: 'rtl',
      lang: 'ar',
      actions: [
        { action: 'open', title: 'فتح' },
        { action: 'close', title: 'إغلاق' }
      ]
    })
  );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event);
  
  event.notification.close();

  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.focus();
          if (urlToOpen !== '/') {
            client.navigate(urlToOpen);
          }
          return;
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

console.log('[SW] DAR AL CODE Service Worker loaded - Privacy Mode');
