import {
  NotificationCategory,
  type NotificationData,
  NotificationGroup,
  type NotificationPayload,
  Priority,
  type SemiPartial,
  Severity,
  assert,
} from '@rotki/common';
import { useSessionStorage } from '@vueuse/core';
import { orderBy } from 'lodash-es';
import { createNotification } from '@/utils/notifications';

function notificationDefaults(): NotificationPayload {
  return {
    category: NotificationCategory.DEFAULT,
    display: false,
    message: '',
    severity: Severity.ERROR,
    title: '',
  };
}

export const useNotificationsStore = defineStore('notifications', () => {
  const data = ref<NotificationData[]>([]);
  const lastDisplay: Ref<Record<string, number>> = useSessionStorage('rotki.notification.last_display', {});

  const { t } = useI18n();

  const prioritized = computed<NotificationData[]>(() => {
    const byDate = orderBy(get(data), n => n.date, 'desc');
    return orderBy(byDate, (n: NotificationData) => n.priority ?? Priority.NORMAL, 'desc');
  });
  const count = computed(() => get(data).length);
  const nextId = computed(() => {
    const ids = get(data)
      .map(value => value.id)
      .sort((a, b) => b - a);

    let nextId: number;
    if (ids.length > 0)
      nextId = ids[0] + 1;
    else nextId = 1;

    return nextId;
  });
  const queue = computed(() => get(prioritized).filter(notification => notification.display));

  function update(payload: NotificationData[]): void {
    set(data, [...get(data), ...payload]);
  }

  function remove(id: number): void {
    const notifications = [...get(data)];

    const index = notifications.findIndex(v => v.id === id);
    if (index > -1)
      notifications.splice(index, 1);

    set(data, notifications);
  }

  function setNotifications(notifications: NotificationData[]): void {
    set(data, notifications);
  }

  const notify = (newData: SemiPartial<NotificationPayload, 'title' | 'message'>): void => {
    const dataList = [...get(data)];

    if (newData.priority === Priority.BULK) {
      const messages = dataList.filter(notification => notification.priority === Priority.BULK)
        .map(notification => notification.message);

      if (messages.includes(newData.message)) {
        return;
      }

      const deserializationErrorPrefix = 'Could not deserialize';

      if (newData.message.startsWith(deserializationErrorPrefix)) {
        const index = dataList.findIndex(notification => notification.group === NotificationGroup.DESERIALIZATION_ERROR);
        if (index >= 0) {
          const existing = dataList[index];
          assert(
            existing.groupCount !== undefined,
            'groupCount should be defined when group is set',
          );
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
          update([
            createNotification(get(nextId), Object.assign(notificationDefaults(), {
              ...newData,
              group: NotificationGroup.DESERIALIZATION_ERROR,
              groupCount: 1,
              message: t('notification_messages.deserialization_error', { count: 1 }),
            })),
          ]);
        }
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

      update([notification]);
    }
    else {
      const notification = dataList[notificationIndex];
      let date = new Date();
      let display = newData.display ?? false;

      const currentTime = date.getTime();
      const group = groupToFind ?? '';
      const lastTime = get(lastDisplay)[group] ?? 0;

      if (currentTime - lastTime < 60_000) {
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
        severity: newData.severity || notification.severity,
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
    nextId,
    notify,
    prioritized,
    queue,
    remove,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useNotificationsStore, import.meta.hot));
