import { ActionTree } from 'vuex';
import store, { RotkehlchenState } from '@/store/store';
import { SessionState } from '@/store/session/state';
import {
  convertToAccountingSettings,
  convertToGeneralSettings
} from '@/data/converters';
import { DBSettings } from '@/model/action-result';
import { service } from '@/services/rotkehlchen_service';
import { monitor } from '@/services/monitoring';
import { notify } from '@/store/notifications/utils';

export const actions: ActionTree<SessionState, RotkehlchenState> = {
  start({ commit }, payload: { premium: boolean; settings: DBSettings }) {
    const { premium, settings } = payload;

    commit('premium', premium);
    commit('premiumSync', settings.premium_should_sync);
    commit('settings', convertToGeneralSettings(settings));
    commit('accountingSettings', convertToAccountingSettings(settings));
  },
  async unlock({ commit, dispatch }, payload: UnlockPayload) {
    try {
      const { username, password, create, syncApproval } = payload;

      const response = await service.unlock_user(
        username,
        password,
        create,
        syncApproval
      );

      commit('newUser', create);
      const db_settings = response.settings;
      if (!db_settings) {
        throw new Error('Unlock Failed');
      }

      await dispatch('start', {
        premium: response.premium,
        settings: db_settings
      });

      monitor.start();

      await dispatch(
        'balances/fetch',
        {
          create,
          exchanges: response.exchanges
        },
        {
          root: true
        }
      );

      commit('logged', true);
    } catch (e) {
      console.error(e);
    }
  },
  async periodicCheck({ commit }) {
    try {
      const result = await service.query_periodic_data();
      if (Object.keys(result).length === 0) {
        // an empty object means user is not logged in yet
        return;
      }

      const {
        last_balance_save,
        eth_node_connection,
        history_process_current_ts
      } = result;

      commit('updateAccountingSetting', {
        lastBalanceSave: last_balance_save
      });
      commit('nodeConnection', eth_node_connection);
      commit('historyProcess', history_process_current_ts);
    } catch (e) {
      notify(`Error at periodic client query: ${e}`, 'Periodic client query');
    }
  }
};

export interface UnlockPayload {
  readonly username: string;
  readonly password: string;
  readonly create: boolean;
  readonly syncApproval: 'yes' | 'no' | 'unknown';
}
