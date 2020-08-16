import { ActionTree } from 'vuex';
import { api } from '@/services/rotkehlchen-api';
import { NotificationState } from '@/store/notifications/state';
import { toNotification } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/store';
import { NotificationBase, Severity } from '@/typing/types';

export const actions: ActionTree<NotificationState, RotkehlchenState> = {
  consume({ commit, getters }): any {
    const title = 'Backend messages';
    api
      .consumeMessages()
      .then(value => {
        let id = getters.nextId;
        const errors = value.errors.map(error =>
          toNotification(error, Severity.ERROR, id++, title)
        );
        const warnings = value.warnings.map(warning =>
          toNotification(warning, Severity.WARNING, id++, title)
        );

        const notifications = errors.concat(warnings);
        if (notifications.length === 0) {
          return;
        }
        commit('update', notifications);
      })
      .catch(reason => {
        commit('update', [
          toNotification(reason, Severity.ERROR, getters.nextId, title)
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
  notify(
    { commit, getters: { nextId } },
    { message, severity, title }: NotificationBase
  ): void {
    const notification = toNotification(message, severity, nextId, title);
    commit('update', [notification]);
  }
};
