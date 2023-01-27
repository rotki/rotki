import { NotificationGroup } from '@rotki/common/lib/messages';
import { useNotificationsStore } from '@/store/notifications';

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
});
