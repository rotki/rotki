import { ActionTree } from 'vuex';
import { api } from '@/services/rotkehlchen-api';
import { NotificationState } from '@/store/notifications/state';
import { toNotification } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/store';
import { Severity } from '@/typing/types';

export const actions: ActionTree<NotificationState, RotkehlchenState> = {
  consume({ commit, getters }): any {
    api
      .consumeMessages()
      .then(value => {
        let id = getters.nextId;
        const errors = value.errors.map(error =>
          toNotification(error, Severity.ERROR, id++)
        );
        const warnings = value.warnings.map(warning =>
          toNotification(warning, Severity.WARNING, id++)
        );

        const notifications = errors.concat(warnings);
        if (notifications.length === 0) {
          return;
        }
        commit('update', notifications);
      })
      .catch(reason => {
        commit('update', [
          toNotification(reason, Severity.ERROR, getters.nextId)
        ]);
      });
  }
};
