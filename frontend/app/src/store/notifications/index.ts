import {
  assert,
  NotificationCategory,
  type NotificationData,
  NotificationGroup,
  type NotificationPayload,
  Priority,
  type SemiPartial,
  Severity,
} from '@rotki/common';
import { useSessionStorage } from '@vueuse/core';
import { orderBy } from 'es-toolkit';
import { createNotification } from '@/utils/notifications';

const DESERIALIZATION_ERROR_PREFIX = 'Could not deserialize';
const NOTIFICATION_COOLDOWN_MS = 60_000;
const NOTIFICATION_MAX_SIZE = 200;

const DEFAULT_NOTIFICATION: NotificationPayload = {
  category: NotificationCategory.DEFAULT,
  display: false,
  message: '',
  severity: Severity.ERROR,
  title: '',
} as const;

function notificationDefaults(): NotificationPayload {
  return { ...DEFAULT_NOTIFICATION };
}

export const useNotificationsStore = defineStore('notifications', () => {
  const data = ref<NotificationData[]>([]);
  const lastDisplay: Ref<Record<string, number>> = useSessionStorage('rotki.notification.last_display', {});
  const messageOverflow = ref(false);

  const { t } = useI18n({ useScope: 'global' });

  const prioritized = computed<NotificationData[]>(() => {
    const byDate = orderBy(get(data), ['date'], ['desc']);
    return orderBy(byDate, [(n: NotificationData): Priority => n.priority ?? Priority.NORMAL], ['desc']);
  });

  const count = computed<number>(() => get(data).length);

  const nextId = computed<number>(() => {
    const ids = get(data)
      .map(value => value.id)
      .sort((a, b) => b - a);

    return ids.length > 0 ? ids[0] + 1 : 1;
  });

  const queue = computed<NotificationData[]>(() => get(prioritized).filter(notification => notification.display));

  function take(notifications: NotificationData[], n: number = NOTIFICATION_MAX_SIZE): NotificationData[] {
    return orderBy(notifications, ['date'], ['desc']).slice(0, n);
  }

  function addNotifications(payload: NotificationData[]): void {
    set(data, take([...get(data), ...payload]));
  }

  function remove(id: number): void {
    const notifications = [...get(data)];

    const index = notifications.findIndex(v => v.id === id);
    if (index > -1)
      notifications.splice(index, 1);

    set(data, notifications);
    set(messageOverflow, false);
  }

  function removeMatching(predicate: (notification: NotificationData) => boolean): void {
    const notifications = [...get(data)];
    const match = notifications.find(predicate);
    if (match !== undefined) {
      remove(match.id);
    }
  }

  function setNotifications(notifications: NotificationData[]): void {
    set(data, take(notifications));
  }

  function handleDeserializationError(dataList: NotificationData[], newData: SemiPartial<NotificationPayload, 'title' | 'message'>): void {
    const index = dataList.findIndex(notification => notification.group === NotificationGroup.DESERIALIZATION_ERROR);

    if (index >= 0) {
      const existing = dataList[index];

      assert(existing.groupCount !== undefined, 'groupCount should be defined when group is set');

      const groupCount = existing.groupCount + 1;

      dataList[index] = {
        ...existing,
        date: new Date(),
        groupCount,
        message: t('notification_messages.deserialization_error', { count: groupCount }),
      };

      set(data, dataList);
    }
    else {
      addNotifications([
        createNotification(get(nextId), Object.assign(notificationDefaults(), {
          ...newData,
          group: NotificationGroup.DESERIALIZATION_ERROR,
          groupCount: 1,
          message: t('notification_messages.deserialization_error', { count: 1 }),
        })),
      ]);
    }
  }

  const notify = (newData: SemiPartial<NotificationPayload, 'title' | 'message'>): void => {
    const notifications = [...get(data)];
    const dataList = take(notifications, NOTIFICATION_MAX_SIZE - 1);

    set(messageOverflow, notifications.length > dataList.length);

    if (newData.priority === Priority.BULK) {
      const messages = dataList.filter(notification => notification.priority === Priority.BULK)
        .map(notification => notification.message);

      if (messages.includes(newData.message)) {
        return;
      }

      if (newData.message.startsWith(DESERIALIZATION_ERROR_PREFIX)) {
        handleDeserializationError(dataList, newData);
        return;
      }
    }

    const groupToFind = newData.group;

    const notificationIndex = groupToFind ? dataList.findIndex(({ group }) => group === groupToFind) : -1;

    if (notificationIndex === -1) {
      const notification = createNotification(get(nextId), Object.assign(notificationDefaults(), newData));

      if (groupToFind && notification.display) {
        set(lastDisplay, {
          ...get(lastDisplay),
          [groupToFind]: notification.date.getTime(),
        });
      }

      addNotifications([notification]);
    }
    else {
      const notification = dataList[notificationIndex];
      let date = new Date();
      let display = newData.display ?? false;

      const currentTime = date.getTime();
      const group = groupToFind ?? '';
      const lastTime = get(lastDisplay)[group] ?? 0;

      if (currentTime - lastTime < NOTIFICATION_COOLDOWN_MS) {
        date = notification.date;
        display = false;
      }

      const newNotification: NotificationData = {
        ...notification,
        action: newData.action,
        date,
        display,
        groupCount: newData.groupCount,
        message: newData.message,
        priority: newData.priority,
        severity: newData.severity ?? notification.severity,
        title: newData.title,
      };

      dataList.splice(notificationIndex, 1);
      dataList.unshift(newNotification);
      set(data, dataList);
    }
  };

  const displayed = (ids: number[]): void => {
    if (ids.length <= 0)
      return;

    const notifications = [...get(data)];
    for (const id of ids) {
      const index = notifications.findIndex(({ id: idA }) => idA === id);
      if (index < 0)
        continue;

      const notification = notifications[index];
      if (notification.group) {
        set(lastDisplay, {
          ...get(lastDisplay),
          [notification.group]: Date.now(),
        });
      }
      notifications[index] = { ...notification, display: false };
    }
    setNotifications(notifications);
  };

  return {
    count,
    data,
    displayed,
    messageOverflow,
    nextId,
    notify,
    prioritized,
    queue,
    remove,
    removeMatching,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useNotificationsStore, import.meta.hot));
