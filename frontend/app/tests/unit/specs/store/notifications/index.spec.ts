import { NotificationGroup, Priority } from '@rotki/common/lib/messages';

describe('store::notifications/index', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test('normal notification', () => {
    const notificationsStore = useNotificationsStore();
    const { data } = storeToRefs(notificationsStore);
    const { notify, remove } = notificationsStore;

    notify({
      title: 'notification-title-1',
      message: 'notification-message-1'
    });

    const dataVal = get(data);

    expect(dataVal).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-1'
      }
    ]);

    remove(dataVal[0].id);
  });

  test('group notification', () => {
    const notificationsStore = useNotificationsStore();
    const { data } = storeToRefs(notificationsStore);
    const { notify } = notificationsStore;

    notify({
      title: 'notification-title-1',
      message: 'notification-message-1',
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      display: true
    });

    expect(get(data)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-1',
        group: NotificationGroup.NEW_DETECTED_TOKENS,
        display: true
      }
    ]);

    const originalDate = get(data)[0].date;

    notify({
      title: 'notification-title-1',
      message: 'notification-message-2',
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: 2,
      display: true
    });

    expect(get(data)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-2',
        group: NotificationGroup.NEW_DETECTED_TOKENS,
        groupCount: 2,
        display: false,
        date: originalDate
      }
    ]);

    vi.advanceTimersByTime(60_000);

    notify({
      title: 'notification-title-1',
      message: 'notification-message-3',
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: 3,
      display: true
    });

    expect(get(data)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-3',
        group: NotificationGroup.NEW_DETECTED_TOKENS,
        groupCount: 3,
        display: true
      }
    ]);
  });

  test('action notification always on top', () => {
    const notificationsStore = useNotificationsStore();
    const { prioritized } = storeToRefs(notificationsStore);
    const { notify } = notificationsStore;
    const actionNotifications = [
      {
        title: 'notification-title-2',
        message: 'notification-message-2',
        i18nParam: { choice: 0, message: '', props: {} },
        priority: Priority.ACTION,
        action: { label: 'Action', action: vi.fn }
      },
      {
        title: 'notification-title-4',
        message: 'notification-message-4',
        i18nParam: { choice: 0, message: '', props: {} },
        priority: Priority.ACTION,
        action: { label: 'Action', action: vi.fn }
      }
    ];

    // normal notification
    notify({
      title: 'notification-title-1',
      message: 'notification-message-1'
    });

    // should be the only notification shown
    expect(get(prioritized)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-1'
      }
    ]);

    // add a notification with action
    notify(actionNotifications[0]);

    // should be on top of the list
    expect(get(prioritized)[0]).toMatchObject(actionNotifications[0]);

    // normal priority notification should go down
    expect(get(prioritized)[1]).toMatchObject({
      title: 'notification-title-1',
      message: 'notification-message-1'
    });

    vi.advanceTimersByTime(60_000);

    // add low priority notification (mostly legacy)
    notify({
      title: 'notification-title-3',
      message: 'notification-message-3',
      priority: Priority.BULK
    });

    // should be at the tail
    expect(get(prioritized)[2]).toMatchObject({
      title: 'notification-title-3',
      message: 'notification-message-3',
      priority: Priority.BULK
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
});
