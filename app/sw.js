self.addEventListener("push", (event) => {
  const payload = event.data
    ? event.data.json()
    : {
        title: "뉴스 알림",
        body: "새 알림이 도착했습니다.",
        url: "/",
      };

  event.waitUntil(
    self.registration.showNotification(payload.title || "뉴스 알림", {
      body: payload.body || "새 알림이 도착했습니다.",
      data: {
        url: payload.url || "/",
        newsId: payload.newsId || null,
      },
      badge: "/assets/eminai_square_icon.png",
      icon: "/assets/eminai_square_icon.png",
      tag: payload.newsId ? `news-${payload.newsId}` : "news-alert",
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if ("focus" in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      return clients.openWindow(targetUrl);
    })
  );
});
