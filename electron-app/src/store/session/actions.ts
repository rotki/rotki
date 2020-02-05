import { ActionTree } from 'vuex';
import { Message, RotkehlchenState } from '@/store/store';
import { SessionState } from '@/store/session/state';
import {
  convertToAccountingSettings,
  convertToGeneralSettings
} from '@/data/converters';
import { DBSettings } from '@/model/action-result';
import { api } from '@/services/rotkehlchen-api';
import { monitor } from '@/services/monitoring';
import { notify } from '@/store/notifications/utils';
import { SyncConflictError } from '@/typing/types';
import { UnlockPayload } from '@/typing/types';

export const actions: ActionTree<SessionState, RotkehlchenState> = {
  start({ commit }, payload: { premium: boolean; settings: DBSettings }) {
    const { premium, settings } = payload;

    commit('premium', premium);
    commit('premiumSync', settings.premium_should_sync);
    commit('settings', convertToGeneralSettings(settings));
    commit('accountingSettings', convertToAccountingSettings(settings));
  },
  async unlock({ commit, dispatch, state }, payload: UnlockPayload) {
    let settings: DBSettings;
    let premium: boolean;
    let exchanges: string[];

    try {
      const { username, create } = payload;
      const isLogged = await api.checkIfLogged(username);
      if (isLogged && !state.syncConflict) {
        [settings, premium, exchanges] = await Promise.all([
          api.getSettings(),
          Promise.resolve(false),
          api.getExchanges()
        ]);
      } else {
        commit('syncConflict', '');
        ({ settings, premium, exchanges } = await api.unlockUser(payload));
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

      commit('login', { username, newAccount: create });
    } catch (e) {
      if (e instanceof SyncConflictError) {
        commit('syncConflict', e.message);
        return;
      }
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
      const result = await api.queryPeriodicData();
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

      if (history_process_current_ts > 0) {
        commit('reports/historyProcess', history_process_current_ts, {
          root: true
        });
      }
    } catch (e) {
      notify(`Error at periodic client query: ${e}`, 'Periodic client query');
    }
  },
  async logout({ commit, state }) {
    try {
      await api.logout(state.username);
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
