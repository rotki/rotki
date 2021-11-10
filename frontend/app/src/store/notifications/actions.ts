import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import {
  handleLegacyMessage,
  handleSnapshotError
} from '@/services/websocket/message-handling';
import { SocketMessageType } from '@/services/websocket/messages';
import { NotificationState } from '@/store/notifications/state';
import { NotificationPayload } from '@/store/notifications/types';
import { createNotification, userNotify } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/types';
import { backoff } from '@/utils/backoff';
import { logger } from '@/utils/logging';

const consume = {
  isRunning: false
};

const unique = function (
  value: string,
  index: number,
  array: string[]
): boolean {
  return array.indexOf(value) === index;
};

const notify = async (message: string, isWarning: boolean) => {
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

export const actions: ActionTree<NotificationState, RotkehlchenState> = {
  async consume({ state: { data } }): Promise<void> {
    if (consume.isRunning) {
      return;
    }

    consume.isRunning = true;
    const title = i18n
      .t('actions.notifications.consume.message_title')
      .toString();

    try {
      const messages = await backoff(3, () => api.consumeMessages(), 10000);
      const existing = data.map(({ message }) => message);
      messages.errors
        .filter(unique)
        .filter(error => !existing.includes(error))
        .forEach(message => notify(message, false));
      messages.warnings
        .filter(unique)
        .filter(warning => !existing.includes(warning))
        .forEach(message => notify(message, true));
    } catch (e: any) {
      const message = e.message || e;
      await userNotify({
        title,
        message,
        display: true
      });
    } finally {
      consume.isRunning = false;
    }
  },
  displayed({ commit, state }, ids: number[]): void {
    if (ids.length <= 0) {
      return;
    }

    const notifications = [...state.data];
    for (let i = 0; i < ids.length; i++) {
      const id = ids[i];
      const index = notifications.findIndex(({ id: idA }) => idA === id);
      if (index < 0) {
        continue;
      }
      notifications[index] = { ...notifications[index], display: false };
    }
    commit('notifications', notifications);
  },
  notify({ commit, getters: { nextId } }, payload: NotificationPayload): void {
    commit('update', [createNotification(nextId, payload)]);
  }
};
