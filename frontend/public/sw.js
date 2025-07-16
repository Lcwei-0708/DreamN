self.addEventListener('push', function(event) {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: 'Notification', body: event.data ? event.data.text() : '' };
  }
  const title = data.title || 'Notification';
  const options = {
    body: data.body || data.content || '',
    icon: '/logo.ico',
    badge: '/logo.ico',
    tag: data.tag || (Date.now().toString() + Math.random()),
    data: {
      url: data.url || '/',
      ...data
    }
  };
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = event.notification.data && event.notification.data.url;
  if (!url) {
    console.warn('[SW] No URL found, redirecting to homepage');
  }
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
      for (let client of windowClients) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(url || '/');
      }
    })
  );
});