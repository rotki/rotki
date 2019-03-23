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
    <div class='title'>${notification.title}</div>
    <div class='body'>
      ${notification.message}
    </div>
  </div>
`;

export interface Notification {
    readonly id: number;
    readonly title: string;
    readonly message: string;
}

export class NotificationManager {

    private notifications: Notification[] = [
        {
            id: 1,
            title: 'Dummy notification',
            message: 'Dummy Message'
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

