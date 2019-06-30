import { ActionTree } from 'vuex';
import { NotificationState } from '@/notifications/state';
import { RotkehlchenState } from '@/store';
import { service } from '@/services/rotkehlchen_service';
import { Severity } from '@/typing/types';
import { toNotification } from '@/notifications/utils';

export const actions: ActionTree<NotificationState, RotkehlchenState> = {
  consume({ commit, getters }): any {
    service
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
