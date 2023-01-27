import { type SemiPartial } from '@rotki/common';
import {
  NotificationCategory,
  type NotificationData,
  type NotificationPayload,
  Severity
} from '@rotki/common/lib/messages';
import { useSessionStorage } from '@vueuse/core';
import { type Ref } from 'vue';
import { useSessionApi } from '@/services/session';
import { backoff } from '@/utils/backoff';
import { uniqueStrings } from '@/utils/data';
import { assert } from '@/utils/assertions';

const notificationDefaults = (): NotificationPayload => ({
  title: '',
  message: '',
  severity: Severity.ERROR,
  display: false,
  category: NotificationCategory.DEFAULT
});

const createNotification = (
  id = 0,
  {
    display,
    duration,
    message,
    severity,
    title,
    action,
    category,
    group,
    groupCount
  }: NotificationPayload = {
    title: '',
    message: '',
    severity: Severity.INFO,
    category: NotificationCategory.DEFAULT
  }
): NotificationData => ({
  title,
  message,
  severity,
  display: display ?? false,
  duration: duration ?? 5000,
  id,
  date: new Date(),
  category,
  action,
  group,
  groupCount
});

export const emptyNotification = (): NotificationData => createNotification();

const createPending = (username: string): Ref<NotificationData[]> => {
  return useSessionStorage(`rotki.notification.pending.${username}`, []);
};

export const useNotificationsStore = defineStore('notifications', () => {
  const data = ref<NotificationData[]>([]);
  const { tc } = useI18n();
  const { consumeMessages } = useSessionApi();
  const { handlePollingMessage } = useMessageHandling();
  const lastDisplay: Ref<Record<string, number>> = useSessionStorage(
    'rotki.notification.last_display',
    {}
  );
  let pending: Ref<NotificationData[] | null> = ref(null);
  let isRunning = false;

  const count = computed(() => get(data).length);
  const nextId = computed(() => {
    const ids = get(data)
      .map(value => value.id)
      .sort((a, b) => b - a);

    let nextId: number;
    if (ids.length > 0) {
      nextId = ids[0] + 1;
    } else {
      nextId = 1;
    }
    return nextId;
  });
  const queue = computed(() =>
    get(data).filter(notification => notification.display)
  );

  function update(payload: NotificationData[]): void {
    set(data, [...get(data), ...payload]);
  }

  function remove(id: number): void {
    const notifications = [...get(data)];

    const index = notifications.findIndex(v => v.id === id);
    if (index > -1) {
      notifications.splice(index, 1);
    }

    set(data, notifications);
  }

  function setNotifications(notifications: NotificationData[]): void {
    set(data, notifications);
  }

  const notify = (
    newData: SemiPartial<NotificationPayload, 'title' | 'message'>
  ): void => {
    const groupToFind = newData.group;
    const dataList = [...get(data)];

    const notificationIndex = groupToFind
      ? dataList.findIndex(({ group }) => group === groupToFind)
      : -1;

    if (notificationIndex === -1) {
      const notification = createNotification(
        get(nextId),
        Object.assign(notificationDefaults(), newData)
      );
      update([notification]);
      if (groupToFind && notification.display) {
        set(lastDisplay, {
          ...get(lastDisplay),
          [groupToFind]: notification.date.getTime()
        });
      }

      if (notification.category === NotificationCategory.ADDRESS_MIGRATION) {
        const notifications = get(pending);
        assert(notifications);
        set(pending, [...notifications, notification]);
      }
    } else {
      const notification = dataList[notificationIndex];
      let date = new Date();
      let display = newData.display ?? false;

      const currentTime = date.getTime();
      const group = groupToFind ?? '';
      const lastTime = get(lastDisplay)[group] ?? 0;

      if (currentTime - lastTime < 60_000) {
        date = notification.date;
        display = false;
      } else {
        set(lastDisplay, { ...get(lastDisplay), [group]: currentTime });
      }
      const newNotification: NotificationData = {
        ...notification,
        date,
        title: newData.title,
        message: newData.message,
        groupCount: newData.groupCount,
        display
      };

      dataList.splice(notificationIndex, 1);
      dataList.unshift(newNotification);
      set(data, dataList);
    }
  };

  function removeFromPending(ids: number[]): void {
    const notifications = get(pending);
    assert(notifications);
    const newPending: NotificationData[] = [];
    notifications.forEach(n => {
      if (!ids.includes(n.id)) {
        newPending.push(n);
      }
    });
    set(pending, newPending);
  }

  const displayed = (ids: number[]): void => {
    if (ids.length <= 0) {
      return;
    }

    const notifications = [...get(data)];
    for (const id of ids) {
      const index = notifications.findIndex(({ id: idA }) => idA === id);
      if (index < 0) {
        continue;
      }
      notifications[index] = { ...notifications[index], display: false };
    }
    setNotifications(notifications);
    removeFromPending(ids);
  };

  const consume = async (): Promise<void> => {
    if (isRunning) {
      return;
    }

    isRunning = true;
    const title = tc('actions.notifications.consume.message_title');

    try {
      const messages = await backoff(3, () => consumeMessages(), 10000);
      const existing = get(data).map(({ message }) => message);
      messages.errors
        .filter(uniqueStrings)
        .filter(error => !existing.includes(error))
        .forEach(message => handlePollingMessage(message, false));
      messages.warnings
        .filter(uniqueStrings)
        .filter(warning => !existing.includes(warning))
        .forEach(message => handlePollingMessage(message, true));
    } catch (e: any) {
      const message = e.message || e;
      notify({
        title,
        message,
        display: true
      });
    } finally {
      isRunning = false;
    }
  };

  const restorePending = () => {
    const notifications = get(pending);
    assert(notifications);
    if (notifications.length > 0) {
      set(data, [...get(data), ...notifications]);
    }
  };

  const initPending = (username: string) => {
    pending = createPending(username);
  };

  return {
    data,
    count,
    nextId,
    queue,
    notify,
    displayed,
    remove,
    consume,
    initPending,
    restorePending
  };
});
