const notificationBadge = (notifications: Notification[]) => `
<i class="fa fa-info-circle fa-fw"></i>
<i class="fa fa-caret-down"></i>
<span class="badge">${notifications.length}</span>
`;

const empty = `
<div class="no-notifications">
    <i class="fa fa-info-circle fa-fw"></i>
    <p>No messages!</p>
</div>
`;

const notificationMessages = (notifications: Notification[]) => `
<div class='notification-area'>
  ${notifications.length > 0 ? notifications.map(value => singleNotification(value)) : empty}
</div>`;

const singleNotification = (notification: Notification) => `
 <div class='notification card card-1' id="${notification.id}">
    <div>
        <div class='title'>${notification.title}</div>
        <div class='body'>
            ${notification.message}
        </div>
    </div>
    <div class="icon">
        <i class="fa ${icon(notification)} fa-2x ${colorClass(notification)}"></i>
    </div>
  </div>
`;

const icon = (notification: Notification) => {
    switch (notification.severity) {
        case Severity.ERROR:
            return 'fa-exclamation-circle';
        case Severity.INFO:
            return 'fa-info-circle';
        case Severity.WARNING:
            return 'fa-exclamation-triangle';
    }
};

const colorClass = (notification: Notification) => {
    switch (notification.severity) {
        case Severity.ERROR:
            return 'text-danger';
        case Severity.INFO:
            return 'text-info';
        case Severity.WARNING:
            return 'text-warning';
    }
};

export interface Notification {
    readonly id: number;
    readonly title: string;
    readonly message: string;
    readonly severity: Severity;
}

export enum Severity {
    WARNING = 'warning',
    ERROR = 'error',
    INFO = 'info'
}

export class NotificationManager {

    private static NOTIFICATION_KEY = 'service_notifications';

    private notifications: Notification[] = [
        {
            id: 1,
            title: 'Dummy Info',
            message: 'Dummy Message',
            severity: Severity.INFO
        },
        {
            id: 2,
            title: 'Dummy Warning',
            message: 'Dummy Message',
            severity: Severity.WARNING
        },
        {
            id: 3,
            title: 'Dummy Error',
            message: 'Dummy Message',
            severity: Severity.ERROR
        },
    ];

    getNotifications(): Notification[] {
        return this.notifications;
    }

    dismissNotification(id: number) {
        const index = this.notifications.findIndex(v => v.id === id);
        if (index > -1) {
            this.notifications.splice(index, 1);
        }
        this.toCache(this.notifications);
    }

    mergeToCache(notifications: Notification[]) {
        const data = this.fromCache().concat(notifications);
        this.toCache(data);
        localStorage.setItem(NotificationManager.NOTIFICATION_KEY, JSON.stringify(data));
        this.notifications = data;
    }

    clearAll() {
        this.notifications = [];
        this.toCache(this.notifications);
    }

    private toCache(notifications: Notification[]) {
        localStorage.setItem(NotificationManager.NOTIFICATION_KEY, JSON.stringify(notifications));
    }

    private fromCache(): Notification[] {
        const stored = localStorage.getItem(NotificationManager.NOTIFICATION_KEY);
        let cached: Notification[] = [];
        if (stored) {
            cached = JSON.parse(stored);
        }
        return cached;
    }
}

export function updateNotifications() {
    const notifications = notificationManager.getNotifications();
    const badge = $('#notification-badge');
    const messages = $('#notification-messages');
    badge.html(notificationBadge(notifications));
    messages.html(notificationMessages(notifications));

    const elements = $('.notification');
    elements.off('click');
    elements.on('click', function (event: JQuery.Event) {
        event.preventDefault();
        notificationManager.dismissNotification(parseInt(this.id, 10));
    });
}

export const notificationManager = new NotificationManager();

