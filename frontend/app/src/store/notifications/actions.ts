import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { Severity } from '@/store/notifications/consts';
import { NotificationState } from '@/store/notifications/state';
import { NotificationPayload } from '@/store/notifications/types';
import { createNotification } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/types';
import { backoff } from '@/utils/backoff';

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

export const actions: ActionTree<NotificationState, RotkehlchenState> = {
  async consume({ commit, getters, state: { data } }): Promise<void> {
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
      let id = getters.nextId;
      const errors = messages.errors
        .filter(unique)
        .filter(error => !existing.includes(error))
        .map(message =>
          createNotification(id++, {
            title,
            message,
            severity: Severity.ERROR,
            display: true
          })
        );
      const warnings = messages.warnings
        .filter(unique)
        .filter(warning => !existing.includes(warning))
        .map(message =>
          createNotification(id++, {
            title,
            message,
            severity: Severity.WARNING
          })
        );

      const notifications = errors.concat(warnings);
      if (notifications.length === 0) {
        return;
      }
      commit('update', notifications);
    } catch (e) {
      const message = e.message || e;
      commit('update', [
        createNotification(getters.nextId, {
          title,
          message,
          severity: Severity.ERROR,
          display: true
        })
      ]);
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
