import { ActionTree } from 'vuex';
import { NotificationState } from '@/store/notifications/state';
import { RotkehlchenState } from '@/store/store';
import { api } from '@/services/rotkehlchen-api';
import { Severity } from '@/typing/types';
import { toNotification } from '@/store/notifications/utils';

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

        commit('update', errors.concat(warnings));
      })
      .catch(reason => {
        commit('update', [
          toNotification(reason, Severity.ERROR, getters.nextId)
        ]);
      });
  }
};
