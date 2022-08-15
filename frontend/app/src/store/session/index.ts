import { BigNumber } from '@rotki/common';
import { ActionResult } from '@rotki/common/lib/data';
import { TimeFramePersist } from '@rotki/common/lib/settings/graphs';
import { ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import { lastLogin } from '@/components/account-management/utils';
import { getBnFormat } from '@/data/amount_formatter';
import { EXTERNAL_EXCHANGES } from '@/data/defaults';
import { interop, useInterop } from '@/electron-interop';
import i18n from '@/i18n';
import { SupportedExternalExchanges } from '@/services/balances/types';
import { monitor } from '@/services/monitoring';
import { api } from '@/services/rotkehlchen-api';
import {
  ALL_CENTRALIZED_EXCHANGES,
  ALL_DECENTRALIZED_EXCHANGES,
  ALL_MODULES
} from '@/services/session/consts';
import { Purgeable } from '@/services/session/types';
import { useAssetInfoRetrieval, useIgnoredAssetsStore } from '@/store/assets';
import { useBalancesStore } from '@/store/balances';
import { Section, Status } from '@/store/const';
import { useDefiStore } from '@/store/defi';
import { useHistory, useTransactions } from '@/store/history';
import { useTxQueryStatus } from '@/store/history/query-status';
import { useMainStore } from '@/store/main';
import { useNotifications } from '@/store/notifications';
import { useReports } from '@/store/reports';
import { usePremiumStore } from '@/store/session/premium';
import { useQueriedAddressesStore } from '@/store/session/queried-addresses';
import { useTagStore } from '@/store/session/tags';
import {
  ChangePasswordPayload,
  NftResponse,
  SyncConflict
} from '@/store/session/types';
import { useWatchersStore } from '@/store/session/watchers';
import { useSettingsStore } from '@/store/settings';
import { useAccountingSettingsStore } from '@/store/settings/accounting';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useStakingStore } from '@/store/staking';
import { useStatisticsStore } from '@/store/statistics';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { getStatusUpdater, showError } from '@/store/utils';
import {
  Exchange,
  SUPPORTED_EXCHANGES,
  SupportedExchange
} from '@/types/exchanges';
import {
  CreateAccountPayload,
  LoginCredentials,
  SyncConflictError,
  UnlockPayload
} from '@/types/login';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { UserSettingsModel } from '@/types/user';
import { backoff } from '@/utils/backoff';
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
  const lastBalanceSave = ref(0);
  const lastDataUpload = ref(0);
  const connectedEthNodes = ref<string[]>([]);
  const showUpdatePopup = ref(false);
  const darkModeEnabled = ref(false);

  const periodicRunning = ref(false);

  const { setMessage } = useMainStore();
  const { awaitTask } = useTasks();
  const { notify } = useNotifications();
  const { fetchWatchers } = useWatchersStore();
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { fetchTags } = useTagStore();
  const frontendSettingsStore = useFrontendSettingsStore();
  const accountingSettingsStore = useAccountingSettingsStore();
  const { update: updateGeneralSettings } = useGeneralSettingsStore();
  const { fetchIgnored } = useHistory();
  const { fetchIgnoredAssets } = useIgnoredAssetsStore();
  const { fetchNetValue } = useStatisticsStore();
  const { fetchSupportedAssets } = useAssetInfoRetrieval();
  const { fetchCounterparties } = useTransactions();
  const { timeframe } = storeToRefs(useSessionSettingsStore());
  const { fetch, refreshPrices } = useBalancesStore();

  const periodicCheck = async () => {
    if (get(periodicRunning)) {
      return;
    }
    set(periodicRunning, true);
    try {
      const result = await backoff(3, () => api.queryPeriodicData(), 10000);
      if (Object.keys(result).length === 0) {
        // an empty object means user is not logged in yet
        return;
      }

      const {
        lastBalanceSave: balance,
        lastDataUploadTs: upload,
        connectedEthNodes: connectedNodes
      } = result;

      if (get(lastBalanceSave) !== balance) {
        set(lastBalanceSave, balance);
      }

      if (get(lastDataUpload) !== upload) {
        set(lastDataUpload, upload);
      }

      set(connectedEthNodes, connectedNodes);
    } catch (e: any) {
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
      set(periodicRunning, false);
    }
  };

  const refreshData = async (exchanges: Exchange[]) => {
    logger.info('Refreshing data');

    const async = [
      fetchIgnored(),
      fetchIgnoredAssets(),
      fetchWatchers(),
      fetch(exchanges),
      fetchNetValue()
    ];

    Promise.all(async).then(() => refreshPrices({ ignoreCache: false }));
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
        const { timeframeSetting, lastKnownTimeframe } = storeToRefs(
          frontendSettingsStore
        );
        const selectedTimeframe = get(timeframeSetting);
        const lastKnown = get(lastKnownTimeframe);
        if (selectedTimeframe !== TimeFramePersist.REMEMBER) {
          set(timeframe, selectedTimeframe);
        } else {
          set(timeframe, lastKnown);
        }
        BigNumber.config({
          FORMAT: getBnFormat(
            frontendSettings.thousandSeparator,
            frontendSettings.decimalSeparator
          )
        });
      }

      set(premium, other.havePremium);
      set(premiumSync, other.premiumShouldSync);
      set(lastBalanceSave, settings.data.lastBalanceSave);
      set(lastDataUpload, settings.data.lastDataUploadTs);
      updateGeneralSettings(settings.general);
      accountingSettingsStore.update(settings.accounting);

      monitor.start();
      await fetchTags();

      set(newAccount, isNew);
      set(username, user);
      set(logged, true);
      await fetchSupportedAssets();
      await fetchCounterparties();

      if (!isNew || sync) {
        await refreshData(exchanges);
      } else {
        const ethUpdater = getStatusUpdater(Section.BLOCKCHAIN_ETH);
        const btcUpdater = getStatusUpdater(Section.BLOCKCHAIN_BTC);
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
      const { settings, exchanges } = await api.createAccount(payload);
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
      const isLogged = await api.checkIfLogged(username);

      let settings: UserSettingsModel;
      let exchanges: Exchange[];
      const conflict = get(syncConflict);
      if (isLogged && !conflict.message) {
        [settings, exchanges] = await Promise.all([
          api.getSettings(),
          api.getExchanges()
        ]);
      } else {
        if (!credentials.username) {
          return { success: false, message: '' };
        }
        set(syncConflict, defaultSyncConflict());
        ({ settings, exchanges } = await api.login(credentials));
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

  async function stop() {
    monitor.stop();
    useBalancesStore().reset();
    useMainStore().reset();
    reset();
    useSettingsStore().reset();
    useDefiStore().reset();
    useStakingStore().reset();
    useStatisticsStore().reset();
    useHistory().reset();
    useTxQueryStatus().reset();
    useNotifications().reset();
    useReports().reset();
    useTasks().reset();
  }

  const logout = async () => {
    interop.resetTray();
    try {
      await api.logout(get(username));
      await stop();
    } catch (e: any) {
      showError(e.message, 'Logout failed');
    }
  };

  const logoutRemoteSession = async (): Promise<ActionStatus> => {
    try {
      const loggedUsers = await api.loggedUsers();
      for (let i = 0; i < loggedUsers.length; i++) {
        const user = loggedUsers[i];
        await api.logout(user);
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
      const success = await api.changeUserPassword(
        get(username),
        currentPassword,
        newPassword
      );
      setMessage({
        description: i18n
          .t('actions.session.password_change.success')
          .toString(),
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
        description: i18n
          .t('actions.session.password_change.error', { message: e.message })
          .toString()
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
  };

  const purgeCache = async (purgeable: Purgeable) => {
    const { purgeExchange } = useHistory();
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

  const reset = () => {
    set(newAccount, false);
    set(logged, false);
    set(loginComplete, false);
    set(username, '');
    set(syncConflict, defaultSyncConflict());
    set(lastBalanceSave, 0);
    set(lastDataUpload, 0);
    set(showUpdatePopup, false);
    set(darkModeEnabled, false);

    usePremiumStore().reset();
    useQueriedAddressesStore().reset();
    useTagStore().reset();
    useWatchersStore().reset();
  };

  return {
    newAccount,
    logged,
    loginComplete,
    username,
    syncConflict,
    lastBalanceSave,
    lastDataUpload,
    showUpdatePopup,
    darkModeEnabled,
    connectedEthNodes,
    login,
    logout,
    logoutRemoteSession,
    createAccount,
    changePassword,
    periodicCheck,
    checkForUpdate,
    purgeCache,
    fetchNfts, //TODO Move it, this does not feel like the right place
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSessionStore, import.meta.hot));
}
