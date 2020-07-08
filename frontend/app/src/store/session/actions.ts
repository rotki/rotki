import { ActionTree } from 'vuex';
import {
  convertToAccountingSettings,
  convertToGeneralSettings
} from '@/data/converters';
import { DBSettings } from '@/model/action-result';
import { monitor } from '@/services/monitoring';
import { api } from '@/services/rotkehlchen-api';
import { notify } from '@/store/notifications/utils';
import { SessionState } from '@/store/session/state';
import { Message, RotkehlchenState } from '@/store/store';
import {
  SettingsUpdate,
  SyncConflictError,
  Tag,
  UnlockPayload
} from '@/typing/types';

export const actions: ActionTree<SessionState, RotkehlchenState> = {
  start({ commit }, payload: { settings: DBSettings }) {
    const { settings } = payload;

    commit('premium', settings.have_premium);
    commit('premiumSync', settings.premium_should_sync);
    commit('generalSettings', convertToGeneralSettings(settings));
    commit('accountingSettings', convertToAccountingSettings(settings));
  },
  async unlock({ commit, dispatch, state }, payload: UnlockPayload) {
    let settings: DBSettings;
    let exchanges: string[];

    try {
      const { username, create } = payload;
      const isLogged = await api.checkIfLogged(username);
      if (isLogged && !state.syncConflict) {
        [settings, exchanges] = await Promise.all([
          api.getSettings(),
          api.getExchanges()
        ]);
      } else {
        commit('syncConflict', '');
        ({ settings, exchanges } = await api.unlockUser(payload));
      }

      await dispatch('balances/fetchSupportedAssets', null, {
        root: true
      });
      await dispatch('balances/fetchManualBalances', null, {
        root: true
      });

      await dispatch('start', {
        settings
      });

      await dispatch('defi/fetchWatchers', null, {
        root: true
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

      commit('tags', await api.getTags());
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
  },

  async addTag({ commit }, tag: Tag) {
    try {
      commit('tags', await api.addTag(tag));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Adding tag',
          description: e.message || ''
        } as Message,
        { root: true }
      );
    }
  },

  async editTag({ commit }, tag: Tag) {
    try {
      commit('tags', await api.editTag(tag));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Editing tag',
          description: e.message || ''
        } as Message,
        { root: true }
      );
    }
  },

  async deleteTag({ commit, dispatch }, tagName: string) {
    try {
      commit('tags', await api.deleteTag(tagName));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Deleting tag',
          description: e.message || ''
        } as Message,
        { root: true }
      );
    }
    dispatch('balances/removeTag', tagName, { root: true });
  },

  async setKrakenAccountType({ commit }, account_type: string) {
    try {
      const settings = await api.setSettings({
        kraken_account_type: account_type
      });
      commit('generalSettings', convertToGeneralSettings(settings));
      commit(
        'setMessage',
        {
          title: 'Success',
          description: 'Succesfully set kraken account type',
          success: true
        } as Message,
        { root: true }
      );
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Error setting kraken account type',
          description: e.message || ''
        } as Message,
        { root: true }
      );
    }
  },

  async updateSettings({ commit }, update: SettingsUpdate): Promise<void> {
    try {
      const settings = await api.setSettings(update);
      commit('generalSettings', convertToGeneralSettings(settings));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Error',
          description: `Setting the main currency was not successful: ${e.message}`,
          success: false
        } as Message,
        { root: true }
      );
    }
  }
};
