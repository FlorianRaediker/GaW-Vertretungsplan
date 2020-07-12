self.addEventListener("activate", event => {
    event.waitUntil(() => {
        idb.open("settings", 1, upgradeDB => {
            const storage = upgradeDB.createObjectStore("settings", {
                keyPath: "key"
            });
            storage.put({key: "hasEnabledPushNotifications", value: false});
        })
    });
})

self.addEventListener("notificationclick", event => {
    const notification = event.notification;
    const primaryKey = notification.data.primaryKey;
    const action = e.action;
    switch (event.action) {
        case "close":
            break;
        default:
            clients.openWindow("https://gawvertretung.florian-raediker.de");
    }
    event.notification.close();
})
