import { BigNumber } from '@rotki/common';
import { ActionResult } from '@rotki/common/lib/data';
import { TimeFramePersist } from '@rotki/common/lib/settings/graphs';
import { ComputedRef } from 'vue';
import { useLastLanguage } from '@/composables/session/language';
import { useStatusUpdater } from '@/composables/status';
import { getBnFormat } from '@/data/amount_formatter';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import { interop, useInterop } from '@/electron-interop';
import { useExchangeApi } from '@/services/balances/exchanges';
import { SupportedExternalExchanges } from '@/services/balances/types';
import { api } from '@/services/rotkehlchen-api';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES
} from '@/services/session/consts';
import { Purgeable } from '@/services/session/types';
import { useUsersApi } from '@/services/session/users.api';
import { useSettingsApi } from '@/services/settings/settings-api';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useBalancesStore } from '@/store/balances';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useDefiStore } from '@/store/defi';
import { useHistory } from '@/store/history';
import { usePurgeStore } from '@/store/history/purge';
import { useTransactions } from '@/store/history/transactions';
import { useMessageStore } from '@/store/message';
import { useMonitorStore } from '@/store/monitor';
import { usePremiumStore } from '@/store/session/premium';
import { useTagStore } from '@/store/session/tags';
import {
  ChangePasswordPayload,
  NftResponse,
  SyncConflict
} from '@/store/session/types';
import { useWatchersStore } from '@/store/session/watchers';
import { useAccountingSettingsStore } from '@/store/settings/accounting';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useStakingStore } from '@/store/staking';
import { useStatisticsStore } from '@/store/statistics';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import {
  Exchange,
  SUPPORTED_EXCHANGES,
  SupportedExchange
} from '@/types/exchanges';
import { SupportedLanguage } from '@/types/frontend-settings';
import {
  CreateAccountPayload,
  LoginCredentials,
  SyncConflictError,
  UnlockPayload
} from '@/types/login';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { UserSettingsModel } from '@/types/user';
import { startPromise } from '@/utils';
import { lastLogin } from '@/utils/account-management';
import { logger } from '@/utils/logging';

const defaultSyncConflict = (): SyncConflict => ({
  message: '',
  payload: null
});

export const useSessionStore = defineStore('session', () => {
  const newAccount = ref(false);
  const logged = ref(false);
  const loginComplete = ref(false);
  const username = ref('');
  const syncConflict = ref<SyncConflict>(defaultSyncConflict());
  const showUpdatePopup = ref(false);
  const darkModeEnabled = ref(false);

  const usersApi = useUsersApi();
  const settingsApi = useSettingsApi();
  const exchangeApi = useExchangeApi();

  const { setMessage } = useMessageStore();
  const { awaitTask } = useTasks();
  const { fetchWatchers } = useWatchersStore();
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { fetchTags } = useTagStore();
  const frontendSettingsStore = useFrontendSettingsStore();
  const accountingSettingsStore = useAccountingSettingsStore();
  const { update: updateGeneralSettings } = useGeneralSettingsStore();
  const { update: updateSessionSettings } = useSessionSettingsStore();
  const { setExchanges } = useExchangeBalancesStore();
  const { fetchIgnored } = useHistory();
  const { fetchIgnoredAssets } = useIgnoredAssetsStore();
  const { fetchNetValue } = useStatisticsStore();
  const { fetchCounterparties } = useTransactions();
  const { fetch, refreshPrices } = useBalancesStore();
  const { start, stop } = useMonitorStore();

  const { t } = useI18n();

  const refreshData = async (): Promise<void> => {
    logger.info('Refreshing data');

    await Promise.allSettled([
      fetchIgnored(),
      fetchIgnoredAssets(),
      fetchWatchers(),
      fetch(),
      fetchNetValue()
    ]);
    await refreshPrices();
  };

  const unlock = async ({
    settings,
    exchanges,
    newAccount: isNew,
    sync,
    username: user
  }: UnlockPayload): Promise<ActionStatus> => {
    try {
      const other = settings.other;
      const frontendSettings = other.frontendSettings;
      if (frontendSettings) {
        frontendSettingsStore.update(frontendSettings);
        const { timeframeSetting, lastKnownTimeframe } = frontendSettings;
        setExchanges(exchanges);
        updateSessionSettings({
          timeframe:
            timeframeSetting !== TimeFramePersist.REMEMBER
              ? timeframeSetting
              : lastKnownTimeframe
        });
        BigNumber.config({
          FORMAT: getBnFormat(
            frontendSettings.thousandSeparator,
            frontendSettings.decimalSeparator
          )
        });
      }

      set(premium, other.havePremium);
      set(premiumSync, other.premiumShouldSync);
      updateGeneralSettings(settings.general);
      accountingSettingsStore.update(settings.accounting);

      start();
      await fetchTags();

      set(newAccount, isNew);
      set(username, user);
      set(logged, true);
      await fetchCounterparties();

      if (!isNew || sync) {
        startPromise(refreshData());
      } else {
        const ethUpdater = useStatusUpdater(Section.BLOCKCHAIN_ETH);
        const btcUpdater = useStatusUpdater(Section.BLOCKCHAIN_BTC);
        ethUpdater.setStatus(Status.LOADED);
        btcUpdater.setStatus(Status.LOADED);
      }

      return { success: true };
    } catch (e: any) {
      logger.error(e);
      if (e instanceof SyncConflictError) {
        set(syncConflict, { message: e.message, payload: e.payload });
        return { success: false, message: '' };
      }
      return { success: false, message: e.message };
    }
  };

  const createAccount = async (
    payload: CreateAccountPayload
  ): Promise<ActionStatus> => {
    try {
      const { settings, exchanges } = await usersApi.createAccount(payload);
      const data: UnlockPayload = {
        settings,
        exchanges,
        username: payload.credentials.username,
        sync: payload.premiumSetup?.syncDatabase,
        newAccount: true
      };
      return await unlock(data);
    } catch (e: any) {
      logger.error(e);
      return { success: false, message: e.message };
    }
  };

  const login = async (
    credentials: LoginCredentials
  ): Promise<ActionStatus> => {
    try {
      const username = credentials.username
        ? credentials.username
        : lastLogin();
      const isLogged = await usersApi.checkIfLogged(username);

      let settings: UserSettingsModel;
      let exchanges: Exchange[];
      const conflict = get(syncConflict);
      if (isLogged && !conflict.message) {
        [settings, exchanges] = await Promise.all([
          settingsApi.getSettings(),
          exchangeApi.getExchanges()
        ]);
      } else {
        if (!credentials.username) {
          return { success: false, message: '' };
        }
        set(syncConflict, defaultSyncConflict());
        ({ settings, exchanges } = await usersApi.login(credentials));
      }

      return await unlock({
        settings,
        exchanges,
        username
      });
    } catch (e: any) {
      logger.error(e);
      if (e instanceof SyncConflictError) {
        set(syncConflict, { message: e.message, payload: e.payload });
        return { success: false, message: '' };
      }
      return { success: false, message: e.message };
    }
  };

  async function cleanup() {
    stop();
    reset();
  }

  const logout = async () => {
    interop.resetTray();
    try {
      await usersApi.logout(get(username));
      await cleanup();
    } catch (e: any) {
      setMessage({
        title: 'Logout failed',
        description: e.message
      });
    }
  };

  const logoutRemoteSession = async (): Promise<ActionStatus> => {
    try {
      const loggedUsers = await usersApi.loggedUsers();
      for (let i = 0; i < loggedUsers.length; i++) {
        const user = loggedUsers[i];
        await usersApi.logout(user);
      }
      return { success: true };
    } catch (e: any) {
      setMessage({
        title: 'Remote session logout failure',
        description: e.message
      });
      return { success: false, message: e.message };
    }
  };

  const checkForUpdate = async (): Promise<void> => {
    const { checkForUpdates } = useInterop();
    set(showUpdatePopup, await checkForUpdates());
  };

  const changePassword = async ({
    currentPassword,
    newPassword
  }: ChangePasswordPayload): Promise<ActionStatus> => {
    const { isPackaged, clearPassword } = useInterop();
    try {
      const success = await usersApi.changeUserPassword(
        get(username),
        currentPassword,
        newPassword
      );
      setMessage({
        description: t('actions.session.password_change.success').toString(),
        success: true
      });

      if (success && isPackaged) {
        clearPassword()
          .then(() => logger.info('clear complete'))
          .catch(e => logger.error(e));
      }

      return {
        success
      };
    } catch (e: any) {
      setMessage({
        description: t('actions.session.password_change.error', {
          message: e.message
        }).toString()
      });
      return {
        success: false,
        message: e.message
      };
    }
  };

  const fetchNfts = async (
    ignoreCache: boolean
  ): Promise<ActionResult<NftResponse | null>> => {
    try {
      const taskType = TaskType.FETCH_NFTS;
      const { taskId } = await api.fetchNfts(ignoreCache);
      const { result } = await awaitTask<NftResponse, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.session.fetch_nfts.task.title').toString(),
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
  };

  const purgeCache = async (purgeable: Purgeable) => {
    const { purgeExchange } = usePurgeStore();
    const { resetState } = useDefiStore();
    const { reset } = useStakingStore();

    if (purgeable === ALL_CENTRALIZED_EXCHANGES) {
      await purgeExchange(ALL_CENTRALIZED_EXCHANGES);
    } else if (purgeable === ALL_DECENTRALIZED_EXCHANGES) {
      resetState(ALL_DECENTRALIZED_EXCHANGES);
    } else if (purgeable === ALL_MODULES) {
      reset();
      resetState(ALL_MODULES);
    } else if (
      SUPPORTED_EXCHANGES.includes(purgeable as SupportedExchange) ||
      EXTERNAL_EXCHANGES.includes(purgeable as SupportedExternalExchanges)
    ) {
      await purgeExchange(purgeable as SupportedExchange);
    } else if (Object.values(Module).includes(purgeable as Module)) {
      if ([Module.ETH2, Module.ADEX].includes(purgeable as Module)) {
        reset(purgeable as Module);
      } else {
        resetState(purgeable as Module);
      }
    }
  };

  const { lastLanguage } = useLastLanguage();
  const { language } = storeToRefs(frontendSettingsStore);

  const adaptiveLanguage: ComputedRef<SupportedLanguage> = computed(() => {
    const selectedLanguageVal = get(lastLanguage);
    return !get(logged) && selectedLanguageVal !== 'undefined'
      ? (selectedLanguageVal as SupportedLanguage)
      : get(language);
  });

  const reset = () => {
    set(newAccount, false);
    set(logged, false);
    set(loginComplete, false);
    set(username, '');
    set(syncConflict, defaultSyncConflict());
    set(showUpdatePopup, false);
    set(darkModeEnabled, false);
  };

  return {
    adaptiveLanguage,
    newAccount,
    logged,
    loginComplete,
    username,
    syncConflict,
    showUpdatePopup,
    darkModeEnabled,
    login,
    logout,
    logoutRemoteSession,
    createAccount,
    changePassword,
    checkForUpdate,
    purgeCache,
    fetchNfts, //TODO Move it, this does not feel like the right place
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSessionStore, import.meta.hot));
}
