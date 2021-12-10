import { SemiPartial } from '@rotki/common';
import { computed, ref } from '@vue/composition-api';
import { defineStore } from 'pinia';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import {
  handleLegacyMessage,
  handleSnapshotError
} from '@/services/websocket/message-handling';
import { SocketMessageType } from '@/services/websocket/messages';
import { Severity } from '@/store/notifications/consts';
import {
  NotificationData,
  NotificationPayload
} from '@/store/notifications/types';
import { backoff } from '@/utils/backoff';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

const notificationDefaults = (): NotificationPayload => ({
  title: '',
  message: '',
  severity: Severity.ERROR,
  display: false
});

const handleNotification = async (message: string, isWarning: boolean) => {
  try {
    const object = JSON.parse(message);
    if (!object.type) {
      await handleLegacyMessage(message, isWarning);
    }

    if (object.type === SocketMessageType.BALANCES_SNAPSHOT_ERROR) {
      await handleSnapshotError(object);
    } else {
      logger.error('unsupported message:', object);
    }
  } catch (e: any) {
    await handleLegacyMessage(message, isWarning);
  }
};

const createNotification = (
  id: number = 0,
  { display, duration, message, severity, title }: NotificationPayload = {
    title: '',
    message: '',
    severity: Severity.INFO
  }
): NotificationData => ({
  title: title,
  message: message,
  severity: severity,
  display: display ?? false,
  duration: duration ?? 5000,
  id: id,
  date: new Date()
});

export const emptyNotification = () => createNotification();

export const useNotifications = defineStore('notifications', () => {
  const data = ref<NotificationData[]>([]);
  let isRunning = false;

  const count = computed(() => data.value.length);
  const nextId = computed(() => {
    const ids = data.value.map(value => value.id).sort((a, b) => b - a);

    let nextId: number;
    if (ids.length > 0) {
      nextId = ids[0] + 1;
    } else {
      nextId = 1;
    }
    return nextId;
  });
  const queue = computed(() =>
    data.value.filter(notification => notification.display)
  );

  function update(payload: NotificationData[]) {
    data.value = [...data.value, ...payload];
  }

  function remove(id: number) {
    const notifications = [...data.value];

    const index = notifications.findIndex(v => v.id === id);
    if (index > -1) {
      notifications.splice(index, 1);
    }

    data.value = notifications;
  }

  function set(notifications: NotificationData[]) {
    data.value = notifications;
  }

  const notify = (
    data: SemiPartial<NotificationPayload, 'title' | 'message'>
  ) => {
    update([
      createNotification(
        nextId.value,
        Object.assign(notificationDefaults(), data)
      )
    ]);
  };

  const displayed = (ids: number[]) => {
    if (ids.length <= 0) {
      return;
    }

    const notifications = [...data.value];
    for (let i = 0; i < ids.length; i++) {
      const id = ids[i];
      const index = notifications.findIndex(({ id: idA }) => idA === id);
      if (index < 0) {
        continue;
      }
      notifications[index] = { ...notifications[index], display: false };
    }
    set(notifications);
  };

  const consume = async (): Promise<void> => {
    if (isRunning) {
      return;
    }

    isRunning = true;
    const title = i18n
      .t('actions.notifications.consume.message_title')
      .toString();

    try {
      const messages = await backoff(3, () => api.consumeMessages(), 10000);
      const existing = data.value.map(({ message }) => message);
      messages.errors
        .filter(uniqueStrings)
        .filter(error => !existing.includes(error))
        .forEach(message => handleNotification(message, false));
      messages.warnings
        .filter(uniqueStrings)
        .filter(warning => !existing.includes(warning))
        .forEach(message => handleNotification(message, true));
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

  const reset = () => {
    data.value = [];
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
    reset
  };
});
