import { ActionTree } from 'vuex';
import { api } from '@/services/rotkehlchen-api';
import { Severity } from '@/store/notifications/consts';
import { NotificationState } from '@/store/notifications/state';
import { NotificationPayload } from '@/store/notifications/types';
import { createNotification } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/types';

const unique = function (
  value: string,
  index: number,
  array: string[]
): boolean {
  return array.indexOf(value) === index;
};

export const actions: ActionTree<NotificationState, RotkehlchenState> = {
  consume({ commit, getters, state: { data } }): any {
    const title = 'Backend messages';
    api
      .consumeMessages()
      .then(value => {
        const existing = data.map(({ message }) => message);
        let id = getters.nextId;
        const errors = value.errors
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
        const warnings = value.warnings
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
      })
      .catch(message => {
        commit('update', [
          createNotification(getters.nextId, {
            title,
            message,
            severity: Severity.ERROR,
            display: true
          })
        ]);
      });
  },
  displayed({ commit, state }, id: number): void {
    const index = state.data.findIndex(notification => notification.id === id);
    if (index < 0) {
      return;
    }
    const notifications = [...state.data];
    notifications[index] = { ...notifications[index], display: false };
    commit('notifications', notifications);
  },
  notify({ commit, getters: { nextId } }, payload: NotificationPayload): void {
    commit('update', [createNotification(nextId, payload)]);
  }
};
