import { ActionResult } from '@rotki/common/lib/data';
import { TimeFramePersist } from '@rotki/common/lib/settings/graphs';
import { ActionTree } from 'vuex';
import { lastLogin } from '@/components/account-management/utils';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { SupportedExternalExchanges } from '@/services/balances/types';
import { balanceKeys } from '@/services/consts';
import { monitor } from '@/services/monitoring';
import { api } from '@/services/rotkehlchen-api';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES
} from '@/services/session/consts';
import {
  Purgeable,
  QueriedAddressPayload,
  Watcher,
  WatcherTypes
} from '@/services/session/types';
import { SYNC_DOWNLOAD, SyncAction } from '@/services/types-api';
import { Section, Status } from '@/store/const';
import { ACTION_PURGE_PROTOCOL } from '@/store/defi/const';
import { HistoryActions } from '@/store/history/consts';
import { useNotifications } from '@/store/notifications';
import { Severity } from '@/store/notifications/consts';
import { useReports } from '@/store/reports';
import {
  ACTION_PURGE_CACHED_DATA,
  SessionActions
} from '@/store/session/const';
import {
  ChangePasswordPayload,
  NftResponse,
  PremiumCredentialsPayload,
  SessionState
} from '@/store/session/types';
import { ACTION_PURGE_DATA } from '@/store/staking/consts';
import { useTasks } from '@/store/tasks';
import { ActionStatus, Message, RotkehlchenState } from '@/store/types';
import { getStatusUpdater, showError, showMessage } from '@/store/utils';
import {
  Exchange,
  KrakenAccountType,
  SUPPORTED_EXCHANGES,
  SupportedExchange
} from '@/types/exchanges';
import {
  LAST_KNOWN_TIMEFRAME,
  TIMEFRAME_SETTING
} from '@/types/frontend-settings';
import {
  CreateAccountPayload,
  LoginCredentials,
  SyncConflictError,
  UnlockPayload
} from '@/types/login';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { SettingsUpdate, Tag, UserSettingsModel } from '@/types/user';
import { backoff } from '@/utils/backoff';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

const periodic = {
  isRunning: false
};

export const actions: ActionTree<SessionState, RotkehlchenState> = {
  async refreshData({ dispatch }, exchanges: Exchange[]) {
    logger.info('Refreshing data');
    const options = {
      root: true
    };
    const async = [
      dispatch(`history/${HistoryActions.FETCH_IGNORED}`, null, options),
      dispatch('fetchIgnoredAssets'),
      dispatch('session/fetchWatchers', null, options),
      dispatch('balances/fetchManualBalances', null, options),
      dispatch('statistics/fetchNetValue', null, options),
      dispatch('balances/fetch', exchanges, options),
      dispatch('balances/fetchLoopringBalances', false, options)
    ];

    Promise.all(async).then(() =>
      dispatch('balances/refreshPrices', { ignoreCache: false }, options)
    );
  },

  async unlock(
    { commit, dispatch, rootState, rootGetters: { status } },
    { settings, exchanges, newAccount, sync, username }: UnlockPayload
  ): Promise<ActionStatus> {
    try {
      const other = settings.other;
      if (other.frontendSettings) {
        commit('settings/restore', other.frontendSettings, {
          root: true
        });
        const timeframeSetting = rootState.settings![TIMEFRAME_SETTING];
        if (timeframeSetting !== TimeFramePersist.REMEMBER) {
          commit('setTimeframe', timeframeSetting);
        } else {
          commit('setTimeframe', rootState.settings![LAST_KNOWN_TIMEFRAME]);
        }
      }

      commit('premium', other.havePremium);
      commit('premiumSync', other.premiumShouldSync);
      commit('updateLastBalanceSave', settings.data.lastBalanceSave);
      commit('updateLastDataUpload', settings.data.lastDataUploadTs);
      commit('generalSettings', settings.general);
      commit('accountingSettings', settings.accounting);

      monitor.start();
      commit('tags', await api.getTags());
      commit('login', { username, newAccount });
      dispatch('balances/fetchSupportedAssets', null, { root: true });

      if (!newAccount || sync) {
        await dispatch('refreshData', exchanges);
      } else {
        const ethUpdater = getStatusUpdater(
          commit,
          Section.BLOCKCHAIN_ETH,
          status
        );
        const btcUpdater = getStatusUpdater(
          commit,
          Section.BLOCKCHAIN_BTC,
          status
        );
        ethUpdater.setStatus(Status.LOADED);
        btcUpdater.setStatus(Status.LOADED);
      }

      return { success: true };
    } catch (e: any) {
      logger.error(e);
      if (e instanceof SyncConflictError) {
        commit('syncConflict', { message: e.message, payload: e.payload });
        return { success: false, message: '' };
      }
      return { success: false, message: e.message };
    }
  },

  async login(
    { state, dispatch, commit },
    credentials: LoginCredentials
  ): Promise<ActionStatus> {
    try {
      const username = credentials.username
        ? credentials.username
        : lastLogin();
      const isLogged = await api.checkIfLogged(username);

      let settings: UserSettingsModel;
      let exchanges: Exchange[];
      if (isLogged && !state.syncConflict.message) {
        [settings, exchanges] = await Promise.all([
          api.getSettings(),
          api.getExchanges()
        ]);
        logger.debug(settings);
      } else {
        if (!credentials.username) {
          return { success: false, message: '' };
        }
        commit('syncConflict', { message: '', payload: null });
        ({ settings, exchanges } = await api.login(credentials));
      }

      return await dispatch('unlock', {
        settings,
        exchanges,
        username
      });
    } catch (e: any) {
      logger.error(e);
      if (e instanceof SyncConflictError) {
        commit('syncConflict', { message: e.message, payload: e.payload });
        return { success: false, message: '' };
      }
      return { success: false, message: e.message };
    }
  },

  async createAccount(
    { dispatch },
    payload: CreateAccountPayload
  ): Promise<ActionStatus> {
    try {
      const { settings, exchanges } = await api.createAccount(payload);
      const data: UnlockPayload = {
        settings,
        exchanges,
        username: payload.credentials.username,
        sync: payload.premiumSetup?.syncDatabase,
        newAccount: true
      };
      return await dispatch('unlock', data);
    } catch (e: any) {
      logger.error(e);
      return { success: false, message: e.message };
    }
  },
  async periodicCheck({
    commit,
    state: {
      lastBalanceSave: lastKnownBalanceSave,
      lastDataUpload,
      nodeConnection
    }
  }) {
    if (periodic.isRunning) {
      return;
    }
    periodic.isRunning = true;
    try {
      const result = await backoff(3, () => api.queryPeriodicData(), 10000);
      if (Object.keys(result).length === 0) {
        // an empty object means user is not logged in yet
        return;
      }

      const { lastBalanceSave, ethNodeConnection, lastDataUploadTs } = result;

      if (lastBalanceSave !== lastKnownBalanceSave) {
        commit('updateLastBalanceSave', lastBalanceSave);
      }

      if (ethNodeConnection !== nodeConnection) {
        commit('nodeConnection', ethNodeConnection);
      }

      if (lastDataUploadTs !== lastDataUpload) {
        commit('updateLastDataUpload', lastDataUploadTs);
      }
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.session.periodic_query.error.title').toString(),
        message: i18n
          .t('actions.session.periodic_query.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
    } finally {
      periodic.isRunning = false;
    }
  },
  async logout({ dispatch, state }) {
    interop.resetTray();
    try {
      await api.logout(state.username);
      await dispatch('stop');
    } catch (e: any) {
      showError(e.message, 'Logout failed');
    }
  },
  async logoutRemoteSession(): Promise<ActionStatus> {
    try {
      const loggedUsers = await api.loggedUsers();
      for (let i = 0; i < loggedUsers.length; i++) {
        const user = loggedUsers[i];
        await api.logout(user);
      }
      return { success: true };
    } catch (e: any) {
      showError(e.message, 'Logout failed');
      return { success: false, message: e.message };
    }
  },
  async stop({ commit }) {
    monitor.stop();
    const opts = { root: true };
    const payload = {};
    commit('session/reset', payload, opts);
    commit('balances/reset', payload, opts);
    commit('defi/reset', payload, opts);
    commit('settings/reset', payload, opts);
    commit('history/reset', payload, opts);
    commit('statistics/reset', payload, opts);
    commit('staking/reset', payload, opts);
    commit('reset', payload, opts);
    useNotifications().reset();
    useReports().reset();
    useTasks().reset();
  },

  async addTag({ commit }, tag: Tag): Promise<ActionStatus> {
    try {
      commit('tags', await api.addTag(tag));
      return {
        success: true
      };
    } catch (e: any) {
      showError(
        e.message,
        i18n.t('actions.session.tag_add.error.title').toString()
      );
      return {
        success: false,
        message: e.message
      };
    }
  },

  async editTag({ commit }, tag: Tag) {
    try {
      commit('tags', await api.editTag(tag));
    } catch (e: any) {
      showError(
        e.message,
        i18n.t('actions.session.tag_edit.error.title').toString()
      );
    }
  },

  async deleteTag({ commit, dispatch }, tagName: string) {
    try {
      commit('tags', await api.deleteTag(tagName));
    } catch (e: any) {
      showError(
        e.message,
        i18n.t('actions.session.tag_delete.error.title').toString()
      );
    }
    dispatch('balances/removeTag', tagName, { root: true });
  },

  async setKrakenAccountType({ commit }, krakenAccountType: KrakenAccountType) {
    try {
      const settings = await api.setSettings({
        krakenAccountType
      });
      commit('generalSettings', settings.general);
      commit(
        'setMessage',
        {
          title: i18n
            .t('actions.session.kraken_account.success.title')
            .toString(),
          description: i18n
            .t('actions.session.kraken_account.success.message')
            .toString(),
          success: true
        } as Message,
        { root: true }
      );
    } catch (e: any) {
      showError(
        e.message,
        i18n.t('actions.session.kraken_account.error.title').toString()
      );
    }
  },

  //TODO: migrate to settingsUpdate in the future
  async updateSettings({ dispatch }, update: SettingsUpdate): Promise<void> {
    const { success, message } = await dispatch('settingsUpdate', update);
    if (!success) {
      showError(
        i18n
          .t('actions.session.settings_update.error.message', { message })
          .toString()
      );
    }
  },

  async settingsUpdate(
    { commit, state },
    update: SettingsUpdate
  ): Promise<ActionStatus> {
    let success = false;
    let message = '';
    try {
      const settings = await api.setSettings(update);
      if (state.premium !== settings.other.havePremium) {
        commit('premium', settings.other.havePremium);
      }

      if (state.premiumSync !== settings.other.premiumShouldSync) {
        commit('premiumSync', settings.other.premiumShouldSync);
      }

      commit('generalSettings', settings.general);
      commit('accountingSettings', settings.accounting);
      success = true;
    } catch (e: any) {
      message = e.message;
    }
    return {
      success,
      message
    };
  },

  async fetchWatchers({ commit, rootState: { session } }) {
    if (!session?.premium) {
      return;
    }

    try {
      const watchers = await api.session.watchers();
      commit('watchers', watchers);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.session.fetch_watchers.error.title').toString(),
        message: i18n
          .t('actions.session.fetch_watchers.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
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
    } catch (e: any) {
      showError(
        i18n
          .t('actions.session.fetch_queriable_address.error.message', {
            message: e.message
          })
          .toString()
      );
    }
  },

  async enableModule(
    { state, dispatch },
    payload: {
      readonly enable: Module[];
      readonly addresses: string[];
    }
  ) {
    const activeModules = state.generalSettings.activeModules;
    const modules: Module[] = [...activeModules, ...payload.enable].filter(
      uniqueStrings
    );
    dispatch('updateSettings', { active_modules: modules });

    for (const module of payload.enable) {
      for (const address of payload.addresses) {
        await dispatch('addQueriedAddress', {
          module,
          address
        });
      }
    }
  },

  async addQueriedAddress({ commit }, payload: QueriedAddressPayload) {
    try {
      const queriedAddresses = await api.session.addQueriedAddress(payload);
      commit('queriedAddresses', queriedAddresses);
    } catch (e: any) {
      showError(
        i18n
          .t('actions.session.add_queriable_address.error.message', {
            message: e.message
          })
          .toString()
      );
    }
  },

  async deleteQueriedAddress({ commit }, payload: QueriedAddressPayload) {
    try {
      const queriedAddresses = await api.session.deleteQueriedAddress(payload);
      commit('queriedAddresses', queriedAddresses);
    } catch (e: any) {
      showError(
        i18n
          .t('actions.session.delete_queriable_address.error.message', {
            message: e.message
          })
          .toString()
      );
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
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  },

  async deletePremium({ commit }): Promise<ActionStatus> {
    try {
      const success = await api.deletePremiumCredentials();
      if (success) {
        commit('premium', false);
      }
      return { success };
    } catch (e: any) {
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
      showMessage(i18n.t('actions.session.password_change.success').toString());
      return {
        success
      };
    } catch (e: any) {
      showError(i18n.t('actions.session.password_change.error').toString());
      return {
        success: false,
        message: e.message
      };
    }
  },

  async fetchIgnoredAssets({ commit }): Promise<void> {
    try {
      const ignoredAssets = await api.assets.ignoredAssets();
      commit('ignoreAssets', ignoredAssets);
    } catch (e: any) {
      const title = i18n.tc('actions.session.ignored_assets.error.title');
      const message = i18n.tc(
        'actions.session.ignored_assets.error.message',
        0,
        {
          error: e.message
        }
      );
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }
  },
  async ignoreAsset({ commit }, asset: string): Promise<ActionStatus> {
    try {
      const ignoredAssets = await api.assets.modifyAsset(true, asset);
      commit('ignoreAssets', ignoredAssets);
      return { success: true };
    } catch (e: any) {
      return { success: false, message: e.message };
    }
  },
  async unignoreAsset({ commit }, asset: string): Promise<ActionStatus> {
    try {
      const ignoredAssets = await api.assets.modifyAsset(false, asset);
      commit('ignoreAssets', ignoredAssets);
      return { success: true };
    } catch (e: any) {
      return { success: false, message: e.message };
    }
  },
  async forceSync({ dispatch }, action: SyncAction): Promise<void> {
    const { isTaskRunning, awaitTask } = useTasks();
    const taskType = TaskType.FORCE_SYNC;
    if (isTaskRunning(taskType).value) {
      return;
    }
    const { notify } = useNotifications();
    try {
      const { taskId } = await api.forceSync(action);
      await awaitTask<boolean, TaskMeta>(taskId, taskType, {
        title: i18n.tc('actions.session.force_sync.task.title'),
        numericKeys: balanceKeys
      });
      const title = i18n.tc('actions.session.force_sync.success.title');
      const message = i18n.tc('actions.session.force_sync.success.message');

      notify({
        title,
        message,
        severity: Severity.INFO,
        display: true
      });

      if (action === SYNC_DOWNLOAD) {
        await dispatch('logout');
      }
    } catch (e: any) {
      const title = i18n.tc('actions.session.force_sync.error.title');
      const message = i18n.tc('actions.session.force_sync.error.message', 0, {
        error: e.message
      });

      notify({
        title,
        message,
        display: true
      });
    }
  },
  async [ACTION_PURGE_CACHED_DATA]({ dispatch }, purgable: Purgeable) {
    const opts = { root: true };
    if (purgable === ALL_CENTRALIZED_EXCHANGES) {
      await dispatch(
        `history/${HistoryActions.PURGE_EXCHANGE}`,
        ALL_CENTRALIZED_EXCHANGES,
        opts
      );
    } else if (purgable === ALL_DECENTRALIZED_EXCHANGES) {
      await dispatch(`defi/${ACTION_PURGE_PROTOCOL}`, Module.UNISWAP, opts);
      await dispatch(`defi/${ACTION_PURGE_PROTOCOL}`, Module.BALANCER, opts);
    } else if (purgable === ALL_MODULES) {
      await dispatch(`staking/${ACTION_PURGE_DATA}`, ALL_MODULES, opts);
      await dispatch(`defi/${ACTION_PURGE_PROTOCOL}`, ALL_MODULES, opts);
    } else if (
      SUPPORTED_EXCHANGES.includes(purgable as SupportedExchange) ||
      EXTERNAL_EXCHANGES.includes(purgable as SupportedExternalExchanges)
    ) {
      await dispatch(
        `history/${HistoryActions.PURGE_EXCHANGE}`,
        purgable,
        opts
      );
    } else if (Object.values(Module).includes(purgable as Module)) {
      if ([Module.ETH2, Module.ADEX].includes(purgable as Module)) {
        await dispatch(`staking/${ACTION_PURGE_DATA}`, purgable, opts);
      } else {
        await dispatch(`defi/${ACTION_PURGE_PROTOCOL}`, purgable, opts);
      }
    }
  },

  async [SessionActions.FETCH_NFTS](
    _,
    payload?: { ignoreCache: boolean }
  ): Promise<ActionResult<NftResponse | null>> {
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.FETCH_NFTS;
      const { taskId } = await api.fetchNfts(payload);
      const { result } = await awaitTask<NftResponse, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.t('actions.session.fetch_nfts.task.title').toString(),
          numericKeys: []
        }
      );
      return {
        result: NftResponse.parse(result),
        message: ''
      };
    } catch (e: any) {
      return {
        result: null,
        message: e.message
      };
    }
  },

  async checkForUpdate({ commit }): Promise<void> {
    const updateAvailable = await window.interop?.checkForUpdates();

    commit('setShowUpdatePopup', updateAvailable);
  },

  async openUpdatePopup({ commit }): Promise<void> {
    commit('setShowUpdatePopup', true);
  },

  async dismissUpdatePopup({ commit }): Promise<void> {
    commit('setShowUpdatePopup', false);
  }
};
