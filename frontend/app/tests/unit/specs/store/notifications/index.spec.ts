import { useNotificationsStore } from '@/store/notifications';
import { NotificationGroup, type NotificationPayload, Priority } from '@rotki/common';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

describe('store::notifications/index', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('normal notification', () => {
    const notificationsStore = useNotificationsStore();
    const { data } = storeToRefs(notificationsStore);
    const { notify, remove } = notificationsStore;

    notify({
      title: 'notification-title-1',
      message: 'notification-message-1',
    });

    const dataVal = get(data);

    expect(dataVal).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-1',
      },
    ]);

    remove(dataVal[0].id);
  });

  it('group notification', () => {
    const notificationsStore = useNotificationsStore();
    const { data } = storeToRefs(notificationsStore);
    const { notify } = notificationsStore;

    notify({
      title: 'notification-title-1',
      message: 'notification-message-1',
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      display: true,
    });

    expect(get(data)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-1',
        group: NotificationGroup.NEW_DETECTED_TOKENS,
        display: true,
      },
    ]);

    const originalDate = get(data)[0].date;

    notify({
      title: 'notification-title-1',
      message: 'notification-message-2',
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: 2,
      display: true,
    });

    expect(get(data)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-2',
        group: NotificationGroup.NEW_DETECTED_TOKENS,
        groupCount: 2,
        display: false,
        date: originalDate,
      },
    ]);

    vi.advanceTimersByTime(60_000);

    notify({
      title: 'notification-title-1',
      message: 'notification-message-3',
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: 3,
      display: true,
    });

    expect(get(data)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-3',
        group: NotificationGroup.NEW_DETECTED_TOKENS,
        groupCount: 3,
        display: true,
      },
    ]);
  });

  it('should keep track of the last time displayed for group notifications', async () => {
    const notificationsStore = useNotificationsStore();
    const { notify } = notificationsStore;

    notify({
      title: 'notification-title-1',
      message: 'notification-message-1',
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      display: true,
    });

    notificationsStore.displayed([1]);
    vi.advanceTimersByTime(60_000);
    expect(notificationsStore.data[0].display).toBe(false);
    await nextTick();
    const sessionKey = sessionStorage.getItem('rotki.notification.last_display') ?? '{}';
    expect(JSON.parse(sessionKey)).toMatchObject(expect.objectContaining({
      [NotificationGroup.NEW_DETECTED_TOKENS]: expect.any(Number),
    }));
  });

  it('action notification always on top', () => {
    const notificationsStore = useNotificationsStore();
    const { prioritized } = storeToRefs(notificationsStore);
    const { notify } = notificationsStore;
    const actionNotifications = [
      {
        title: 'notification-title-2',
        message: 'notification-message-2',
        i18nParam: { choice: 0, message: '', props: {} },
        priority: Priority.ACTION,
        action: { label: 'Action', action: vi.fn },
      },
      {
        title: 'notification-title-4',
        message: 'notification-message-4',
        i18nParam: { choice: 0, message: '', props: {} },
        priority: Priority.ACTION,
        action: { label: 'Action', action: vi.fn },
      },
    ];

    // normal notification
    notify({
      title: 'notification-title-1',
      message: 'notification-message-1',
    });

    // should be the only notification shown
    expect(get(prioritized)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-1',
      },
    ]);

    // add a notification with action
    notify(actionNotifications[0]);

    // should be on top of the list
    expect(get(prioritized)[0]).toMatchObject(actionNotifications[0]);

    // normal priority notification should go down
    expect(get(prioritized)[1]).toMatchObject({
      title: 'notification-title-1',
      message: 'notification-message-1',
    });

    vi.advanceTimersByTime(60_000);

    // add low priority notification (mostly legacy)
    notify({
      title: 'notification-title-3',
      message: 'notification-message-3',
      priority: Priority.BULK,
    });

    // should be at the tail
    expect(get(prioritized)[2]).toMatchObject({
      title: 'notification-title-3',
      message: 'notification-message-3',
      priority: Priority.BULK,
    });

    // action notification should still be on top
    expect(get(prioritized)[0]).toMatchObject(actionNotifications[0]);

    // add another action notification
    notify(actionNotifications[1]);

    // new action notification should be on top
    expect(get(prioritized)[0]).toMatchObject(actionNotifications[1]);

    // first action notification should be second
    expect(get(prioritized)[1]).toMatchObject(actionNotifications[0]);
  });

  it('should not notify a second time if a bulk notification with the same message exists', () => {
    const notificationsStore = useNotificationsStore();
    const { notify } = notificationsStore;

    const getMessage = (): NotificationPayload => ({
      priority: Priority.BULK,
      message: 'there was a problem',
      title: 'backend',
      severity: Severity.WARNING,
      category: NotificationCategory.DEFAULT,
    });

    notify(getMessage());
    notify(getMessage());

    expect(notificationsStore.data).toHaveLength(1);
    expect(notificationsStore.data[0]).toMatchObject(getMessage());
  });

  it('should not notify add more notifications for deserialization errors', () => {
    const notificationsStore = useNotificationsStore();
    const { notify } = notificationsStore;

    const getMessage = (count: number): NotificationPayload => ({
      priority: Priority.BULK,
      message: `Could not deserialize asset ${count}`,
      title: 'backend',
      severity: Severity.WARNING,
      category: NotificationCategory.DEFAULT,
    });

    for (let i = 0; i < 10; i++) {
      notify(getMessage(i));
    }

    expect(notificationsStore.data).toHaveLength(1);
    expect(notificationsStore.data[0]).toMatchObject({
      ...getMessage(0),
      message: 'notification_messages.deserialization_error::10',
    });
  });

  it('should not keep more than 200 notifications stored', () => {
    const notificationsStore = useNotificationsStore();
    const { notify } = notificationsStore;

    const getMessage = (count: number): NotificationPayload => ({
      priority: Priority.BULK,
      message: `Warning number ${count + 1}`,
      title: 'backend',
      severity: Severity.WARNING,
      category: NotificationCategory.DEFAULT,
    });

    for (let i = 0; i < 205; i++) {
      notify(getMessage(i));
      vi.advanceTimersByTime(1_000);
    }

    expect(notificationsStore.data).toHaveLength(200);
    expect(notificationsStore.data[0]).toMatchObject({
      ...getMessage(204),
    });
    expect(notificationsStore.data[199]).toMatchObject({
      ...getMessage(5),
    });
    expect(notificationsStore.messageOverflow).toBe(true);
  });

  it('should mark a notification as displayed when the proper method is called', () => {
    const notificationsStore = useNotificationsStore();
    const { notify } = notificationsStore;

    const getMessage = (count: number): NotificationPayload => ({
      priority: Priority.BULK,
      message: `Warning number ${count + 1}`,
      title: 'backend',
      severity: Severity.ERROR,
      category: NotificationCategory.DEFAULT,
      display: true,
    });

    notify(getMessage(0));
    notify(getMessage(1));

    expect(notificationsStore.data).toHaveLength(2);
    expect(notificationsStore.data[0]).toMatchObject({
      ...getMessage(0),
    });

    notificationsStore.displayed([1]);

    expect(notificationsStore.data[0]).toMatchObject({
      ...getMessage(0),
      display: false,
    });
    expect(notificationsStore.messageOverflow).toBe(false);
  });
});
