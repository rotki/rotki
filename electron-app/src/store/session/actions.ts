import { ActionTree } from 'vuex';
import { Message, RotkehlchenState } from '@/store/store';
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

      const { settings, premium, exchanges } = response;

      if (!settings) {
        commit(
          'setMessage',
          {
            title: 'Unlock failed',
            description: response.message || response.error || ''
          } as Message,
          { root: true }
        );
        return;
      }

      await dispatch('start', {
        premium,
        settings
      });

      monitor.start();

      await dispatch(
        'balances/fetch',
        {
          create,
          exchanges
        },
        {
          root: true
        }
      );

      commit('login', { username, newUser: create });
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Login failed',
          description: e.message,
          success: false
        },
        { root: true }
      );
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
      commit('reports/historyProcess', history_process_current_ts, {
        root: true
      });
    } catch (e) {
      notify(`Error at periodic client query: ${e}`, 'Periodic client query');
    }
  },
  async logout({ commit }) {
    try {
      await service.logout();
      monitor.stop();
      commit('session/reset', {}, { root: true });
      commit('notifications/reset', {}, { root: true });
      commit('reports/reset', {}, { root: true });
      commit('balances/reset', {}, { root: true });
      commit('tasks/reset', {}, { root: true });
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Logout failed',
          description: e.message || ''
        } as Message,
        { root: true }
      );
    }
  }
};

export interface UnlockPayload {
  readonly username: string;
  readonly password: string;
  readonly create: boolean;
  readonly syncApproval: 'yes' | 'no' | 'unknown';
}
