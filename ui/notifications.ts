export enum Severity {
    WARNING = 'warning',
    ERROR = 'error',
    INFO = 'info'
}

export interface Notification {
    readonly id: number;
    readonly title: string;
    readonly message: string;
    readonly severity: Severity;
}

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

const notificationBadge = (notifications: Notification[]) => `
<i class="fa fa-bell fa-fw"></i>
<i class="fa fa-caret-down"></i>
<span class="badge">${notifications.length}</span>
`;

const empty = `
<div class="no-notifications">
    <i class="fa fa-info-circle fa-fw"></i>
    <p>No messages!</p>
</div>
`;

const singleNotification = (notification: Notification) => `
<div class='notification card card-1' id="notification-${notification.id}">
    <div>
        <div class='title'>${notification.title}</div>
        <div class='body'>
            ${notification.message}
        </div>
    </div>
    <div class="icons">
        <div data-tooltip="Dismisses notification" class="tooltip-left">
            <i class="fa fa-close fa-2x notification-dismiss"></i>
        </div>
        <i class="fa ${icon(notification)} fa-2x ${colorClass(notification)} icon"></i>
    </div>
</div>
`;

const notificationMessages = (notifications: Notification[]) => `
<div class="notification-clear tooltip-right" data-tooltip="Clears all notifications">
    <i class="fa fa-trash fa-1x" id="notifications-clear-all"></i>
</div>
<div class='notification-area'>
  ${notifications.length > 0 ? notifications.reverse().map(value => singleNotification(value)).join('') : empty}
</div>`;

export class NotificationManager {

    private static NOTIFICATION_KEY = 'service_notifications';

    private notifications: Notification[] = [];

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

    getNextId(): number {
        const ids = this.notifications.map(value => value.id)
            .sort((a, b) => b - a);

        let nextId: number;
        if (ids.length > 0) {
            nextId = ids[0] + 1;
        } else {
            nextId = 1;
        }
        return nextId;
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

export const notificationManager = new NotificationManager();

function updateNotificationMessages(notifications: Notification[]) {
    const elements = $('.notification');
    for (const notification of notifications) {
        const element = elements.filter(`#notification-${notification.id}`);
        if (element.html()) {
            continue;
        }
        $('.notification-area').prepend(singleNotification(notification));
    }

}

export function updateNotifications() {
    const notifications = notificationManager.getNotifications();
    const badge = $('#notification-badge');
    const messages = $('#notification-messages');

    badge.html(notificationBadge(notifications));
    const content = $('.notification-area').children();
    if (content.length === 0) {
        messages.html(notificationMessages(notifications));
    } else {
        updateNotificationMessages(notifications);
    }

}

export function setupNotificationHandlers() {
    const $notification = $('.notification-dismiss');

    const $clear = $('#notifications-clear-all');
    $notification.off('click');

    $clear.off('click');

    $notification.on('click', function (event: JQuery.Event) {
        event.preventDefault();
        const notification = $(event.target).closest('.notification');
        const id = notification.attr('id');
        if (id) {
            const notificationId = parseInt(id.replace('notification-', ''), 10);
            notification.remove();
            notificationManager.dismissNotification(notificationId);
            const badge = $('.badge');
            badge.text(parseInt(badge.text(), 10) - 1);
        }
    });

    $clear.on('click', function (event: JQuery.Event) {
        event.preventDefault();

        const confirm = () => {
            notificationManager.clearAll();
            $('.badge').text(0);
            $('.notification-area').html(empty);
        };

        $.confirm({
            title: 'Clear active notifications',
            content: 'This action will clear all the active notifications. Do you want to proceed?',
            buttons: {
                confirm: confirm,
                cancel: () => {
                }
            }
        });

    });

}

