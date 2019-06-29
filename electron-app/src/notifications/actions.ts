import { ActionTree } from 'vuex';
import { NotificationState } from '@/notifications/state';
import { RotkehlchenState } from '@/store';
import { service } from '@/services/rotkehlchen_service';
import { NotificationData, Severity } from '@/typing/types';

const toNotification = (
  message: string,
  severity: Severity,
  id: number
): NotificationData => ({
  title: '',
  message: message,
  severity: severity,
  id: id
});

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
