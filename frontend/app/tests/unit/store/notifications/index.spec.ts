import { NotificationGroup } from '@rotki/common/lib/messages';
import { useNotificationsStore } from '@/store/notifications';

describe('store::notifications/index', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
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
      group: NotificationGroup.NEW_DETECTED_TOKENS
    });

    expect(get(data)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-1',
        group: NotificationGroup.NEW_DETECTED_TOKENS
      }
    ]);

    notify({
      title: 'notification-title-1',
      message: 'notification-message-2',
      group: NotificationGroup.NEW_DETECTED_TOKENS,
      groupCount: 2
    });

    expect(get(data)).toMatchObject([
      {
        title: 'notification-title-1',
        message: 'notification-message-2',
        group: NotificationGroup.NEW_DETECTED_TOKENS,
        groupCount: 2
      }
    ]);
  });
});
