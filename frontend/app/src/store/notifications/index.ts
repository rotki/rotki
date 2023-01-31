import { type SemiPartial } from '@rotki/common';
import {
  NotificationCategory,
  type NotificationData,
  type NotificationPayload,
  Severity
} from '@rotki/common/lib/messages';
import { useSessionStorage } from '@vueuse/core';
import { type Ref } from 'vue';

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

export const useNotificationsStore = defineStore('notifications', () => {
  const data: Ref<NotificationData[]> = ref([]);
  const lastDisplay: Ref<Record<string, number>> = useSessionStorage(
    'rotki.notification.last_display',
    {}
  );

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

      if (groupToFind && notification.display) {
        set(lastDisplay, {
          ...get(lastDisplay),
          [groupToFind]: notification.date.getTime()
        });
      }

      update([notification]);
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
      const notification = notifications[index];
      if (notification.group) {
        set(lastDisplay, {
          ...get(lastDisplay),
          [notification.group]: Date.now()
        });
      }
      notifications[index] = { ...notification, display: false };
    }
    setNotifications(notifications);
  };

  return {
    data,
    count,
    nextId,
    queue,
    notify,
    displayed,
    remove
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useNotificationsStore, import.meta.hot)
  );
}
