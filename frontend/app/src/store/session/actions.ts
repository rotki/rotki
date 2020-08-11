import { ActionTree } from 'vuex';
import {
  convertToAccountingSettings,
  convertToGeneralSettings
} from '@/data/converters';
import { DBSettings } from '@/model/action-result';
import { monitor } from '@/services/monitoring';
import { api } from '@/services/rotkehlchen-api';
import {
  QueriedAddressPayload,
  Watcher,
  WatcherTypes
} from '@/services/session/types';
import { notify } from '@/store/notifications/utils';
import {
  ChangePasswordPayload,
  PremiumCredentialsPayload,
  SessionState
} from '@/store/session/types';
import { loadFrontendSettings } from '@/store/settings/utils';
import { Message, RotkehlchenState } from '@/store/store';
import { ActionStatus } from '@/store/types';
import { showError, showMessage } from '@/store/utils';
import {
  SettingsUpdate,
  Severity,
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

      if (settings.frontend_settings) {
        loadFrontendSettings(commit, settings.frontend_settings);
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

      await dispatch('session/fetchWatchers', null, {
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
        history_process_current_ts,
        history_process_start_ts
      } = result;

      commit('updateAccountingSetting', {
        lastBalanceSave: last_balance_save
      });
      commit('nodeConnection', eth_node_connection);

      if (history_process_current_ts > 0) {
        commit(
          'reports/historyProcess',
          {
            start: history_process_start_ts,
            current: history_process_current_ts
          },
          {
            root: true
          }
        );
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
      commit('defi/reset', {}, { root: true });
      commit('tasks/reset', {}, { root: true });
      commit('settings/reset', {}, { root: true });
    } catch (e) {
      showError(e.message, 'Logout failed');
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
      showError(e.message, 'Error setting kraken account type');
    }
  },

  async updateSettings({ commit }, update: SettingsUpdate): Promise<void> {
    try {
      const settings = await api.setSettings(update);
      commit('generalSettings', convertToGeneralSettings(settings));
    } catch (e) {
      showError(`Updating settings was not successful: ${e.message}`);
    }
  },

  async fetchWatchers({ commit, rootState: { session } }) {
    if (!session?.premium) {
      return;
    }

    try {
      const watchers = await api.session.watchers();
      commit('watchers', watchers);
    } catch (e) {
      notify(`Error: ${e}`, 'Fetching watchers', Severity.ERROR);
    }
  },

  async addWatchers(
    { commit },
    watchers: Omit<Watcher<WatcherTypes>, 'identifier'>[]
  ) {
    const updatedWatchers = await api.session.addWatcher(watchers);
    commit('watchers', updatedWatchers);
    return updatedWatchers;
  },

  async deleteWatchers({ commit }, identifiers: string[]) {
    const updatedWatchers = await api.session.deleteWatcher(identifiers);
    commit('watchers', updatedWatchers);
    return updatedWatchers;
  },

  async editWatchers({ commit }, watchers: Watcher<WatcherTypes>[]) {
    const updatedWatchers = await api.session.editWatcher(watchers);
    commit('watchers', updatedWatchers);
    return updatedWatchers;
  },

  async fetchQueriedAddresses({ commit }) {
    try {
      const queriedAddresses = await api.session.queriedAddresses();
      commit('queriedAddresses', queriedAddresses);
    } catch (e) {
      showError(`Failure to fetch the queriable addresses: ${e.message}`);
    }
  },

  async addQueriedAddress({ commit }, payload: QueriedAddressPayload) {
    try {
      const queriedAddresses = await api.session.addQueriedAddress(payload);
      commit('queriedAddresses', queriedAddresses);
    } catch (e) {
      showError(`Failure to add a queriable address: ${e.message}`);
    }
  },

  async deleteQueriedAddress({ commit }, payload: QueriedAddressPayload) {
    try {
      const queriedAddresses = await api.session.deleteQueriedAddress(payload);
      commit('queriedAddresses', queriedAddresses);
    } catch (e) {
      showError(`Failure to delete a queriable address: ${e.message}`);
    }
  },

  async setupPremium(
    { commit },
    { apiKey, apiSecret, username }: PremiumCredentialsPayload
  ): Promise<ActionStatus> {
    try {
      const success = await api.setPremiumCredentials(
        username,
        apiKey,
        apiSecret
      );

      if (success) {
        commit('premium', true);
      }
      return { success };
    } catch (e) {
      return {
        success: false,
        message: e.message
      };
    }
  },

  async deletePremium({ commit }, username: string): Promise<ActionStatus> {
    try {
      const success = await api.deletePremiumCredentials(username);
      if (success) {
        commit('premium', false);
      }
      return { success };
    } catch (e) {
      return {
        success: false,
        message: e.message
      };
    }
  },

  async changePassword(
    { state: { username } },
    { currentPassword, newPassword }: ChangePasswordPayload
  ): Promise<ActionStatus> {
    try {
      const success = await api.changeUserPassword(
        username,
        currentPassword,
        newPassword
      );
      showMessage('Successfully changed user password');
      return {
        success
      };
    } catch (e) {
      showError('Error while changing the user password');
      return {
        success: false,
        message: e.message
      };
    }
  }
};
