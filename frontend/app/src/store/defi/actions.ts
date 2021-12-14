import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { AaveBalances, AaveHistory } from '@rotki/common/lib/defi/aave';
import { XswapBalances, XswapEvents } from '@rotki/common/lib/defi/xswap';
import { ActionContext, ActionTree } from 'vuex';
import i18n from '@/i18n';
import { balanceKeys } from '@/services/consts';
import {
  aaveHistoryKeys,
  dsrKeys,
  ProtocolVersion,
  vaultDetailsKeys,
  vaultKeys
} from '@/services/defi/consts';
import { ApiMakerDAOVault } from '@/services/defi/types';
import {
  CompoundBalances,
  CompoundHistory
} from '@/services/defi/types/compound';
import {
  YearnVaultsBalances,
  YearnVaultsHistory
} from '@/services/defi/types/yearn';
import { api } from '@/services/rotkehlchen-api';
import { ALL_MODULES } from '@/services/session/consts';
import { Section, Status } from '@/store/const';
import {
  ACTION_PURGE_PROTOCOL,
  dexTradeNumericKeys,
  uniswapEventsNumericKeys,
  uniswapNumericKeys
} from '@/store/defi/const';
import { convertMakerDAOVaults } from '@/store/defi/converters';
import { DefiMutations } from '@/store/defi/mutation-types';
import { defaultCompoundHistory } from '@/store/defi/state';
import {
  Airdrops,
  AllDefiProtocols,
  DefiState,
  DexTrades,
  DSRBalances,
  DSRHistory,
  MakerDAOVaultDetails
} from '@/store/defi/types';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { RotkehlchenState } from '@/store/types';
import { fetchAsync, isLoading, setStatus } from '@/store/utils';
import { Module } from '@/types/modules';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { Zero } from '@/utils/bignumbers';

export const actions: ActionTree<DefiState, RotkehlchenState> = {
  async fetchDSRBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.MAKERDAO_DSR)) {
      return;
    }
    const section = Section.DEFI_DSR_BALANCES;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);

    const { awaitTask } = useTasks();

    try {
      const taskType = TaskType.DSR_BALANCE;
      const { taskId } = await api.defi.dsrBalance();
      const { result } = await awaitTask<DSRBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.dsr_balances.task.title'),
          numericKeys: dsrKeys
        }
      );
      commit('dsrBalances', result);
    } catch (e: any) {
      const message = i18n.tc(
        'actions.defi.dsr_balances.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = i18n.tc('actions.defi.dsr_balances.error.title');
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }

    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchDSRHistory(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.MAKERDAO_DSR) || !session?.premium) {
      return;
    }
    const section = Section.DEFI_DSR_HISTORY;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();

    try {
      const taskType = TaskType.DSR_HISTORY;
      const { taskId } = await api.defi.dsrHistory();
      const { result } = await awaitTask<DSRHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.dsr_history.task.title'),
          numericKeys: balanceKeys
        }
      );

      commit('dsrHistory', result);
    } catch (e: any) {
      const message = i18n.tc(
        'actions.defi.dsr_history.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = i18n.tc('actions.defi.dsr_history.error.title');
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchMakerDAOVaults(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.MAKERDAO_VAULTS)) {
      return;
    }
    const section = Section.DEFI_MAKERDAO_VAULTS;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.MAKEDAO_VAULTS;
      const { taskId } = await api.defi.makerDAOVaults();
      const { result } = await awaitTask<ApiMakerDAOVault[], TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.makerdao_vaults.task.title'),
          numericKeys: vaultKeys
        }
      );

      commit('makerDAOVaults', convertMakerDAOVaults(result));
    } catch (e: any) {
      const message = i18n.tc(
        'actions.defi.makerdao_vaults.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = i18n.tc('actions.defi.makerdao_vaults.error.title');
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchMakerDAOVaultDetails(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.MAKERDAO_VAULTS) || !session?.premium) {
      return;
    }
    const section = Section.DEFI_MAKERDAO_VAULT_DETAILS;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);

    const { awaitTask } = useTasks();

    try {
      const { taskId } = await api.defi.makerDAOVaultDetails();
      const { result } = await awaitTask<MakerDAOVaultDetails[], TaskMeta>(
        taskId,
        TaskType.MAKERDAO_VAULT_DETAILS,
        {
          title: i18n.tc('actions.defi.makerdao_vault_details.task.title'),
          numericKeys: vaultDetailsKeys
        }
      );

      commit('makerDAOVaultDetails', result);
    } catch (e: any) {
      const message = i18n.tc(
        'actions.defi.makerdao_vault_details.error.description',
        undefined,
        { error: e.message }
      );
      const title = i18n.tc('actions.defi.makerdao_vault_details.error.title');
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }

    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchAaveBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.AAVE)) {
      return;
    }
    const section = Section.DEFI_AAVE_BALANCES;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();

    try {
      const taskType = TaskType.AAVE_BALANCES;
      const { taskId } = await api.defi.fetchAaveBalances();
      const { result } = await awaitTask<AaveBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.aave_balances.task.title'),
          numericKeys: balanceKeys
        }
      );

      commit('aaveBalances', result);
    } catch (e: any) {
      const message = i18n.tc(
        'actions.defi.aave_balances.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = i18n.tc('actions.defi.aave_balances.error.title');
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }

    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchAaveHistory(
    { commit, rootGetters: { status }, rootState: { session } },
    payload: { refresh?: boolean; reset?: boolean }
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.AAVE) || !session?.premium) {
      return;
    }
    const section = Section.DEFI_AAVE_HISTORY;
    const currentStatus = status(section);
    const refresh = payload?.refresh;
    const reset = payload?.reset;

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();

    try {
      const taskType = TaskType.AAVE_HISTORY;
      const { taskId } = await api.defi.fetchAaveHistory(reset);
      const { result } = await awaitTask<AaveHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.aave_history.task.title'),
          numericKeys: aaveHistoryKeys
        }
      );

      commit('aaveHistory', result);
    } catch (e: any) {
      const message = i18n.tc(
        'actions.defi.aave_history.error.description',
        undefined,
        { error: e.message }
      );
      const title = i18n.tc('actions.defi.aave_history.error.title');
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }

    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchDefiBalances(
    { commit, rootGetters: { status } },
    refresh: boolean
  ) {
    const section = Section.DEFI_BALANCES;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    setStatus(Status.LOADING, section, status, commit);

    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.DEFI_BALANCES;
      const { taskId } = await api.defi.fetchAllDefi();
      const { result } = await awaitTask<AllDefiProtocols, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.balances.task.title'),
          numericKeys: balanceKeys
        }
      );

      commit('allDefiProtocols', result);
    } catch (e: any) {
      const title = i18n.tc('actions.defi.balances.error.title');
      const message = i18n.tc(
        'actions.defi.balances.error.description',
        undefined,
        { error: e.message }
      );
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchAllDefi(
    { commit, dispatch, rootGetters: { status } },
    refresh: boolean = false
  ) {
    const section = Section.DEFI_OVERVIEW;
    const currentStatus = status(section);
    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    await dispatch('fetchDefiBalances', refresh);
    setStatus(Status.PARTIALLY_LOADED, section, status, commit);

    await Promise.all([
      dispatch('fetchAaveBalances', refresh),
      dispatch('fetchDSRBalances', refresh),
      dispatch('fetchMakerDAOVaults', refresh),
      dispatch('fetchCompoundBalances', refresh),
      dispatch('fetchYearnVaultBalances', {
        refresh,
        version: ProtocolVersion.V1
      }),
      dispatch('fetchYearnVaultBalances', {
        refresh,
        version: ProtocolVersion.V2
      }),
      dispatch('liquity/fetchBalances', refresh)
    ]);

    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchLending(
    { commit, dispatch, rootState: { session }, rootGetters: { status } },
    refresh?: boolean
  ) {
    const premium = session?.premium;
    const section = Section.DEFI_LENDING;
    const premiumSection = Section.DEFI_LENDING_HISTORY;
    const currentStatus = status(section);

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;

    if (
      !isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && refresh)
    ) {
      setStatus(newStatus, section, status, commit);

      await Promise.all([
        dispatch('fetchDSRBalances', refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED, section, status, commit);
        }),
        dispatch('fetchAaveBalances', refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED, section, status, commit);
        }),
        dispatch('fetchCompoundBalances', refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED, section, status, commit);
        }),
        dispatch('fetchYearnVaultBalances', {
          refresh,
          version: ProtocolVersion.V1
        }).then(() => {
          setStatus(Status.PARTIALLY_LOADED, section, status, commit);
        }),
        dispatch('fetchYearnVaultBalances', {
          refresh,
          version: ProtocolVersion.V2
        }).then(() => {
          setStatus(Status.PARTIALLY_LOADED, section, status, commit);
        })
      ]);

      setStatus(Status.LOADED, section, status, commit);
    }

    const currentPremiumStatus = status(premiumSection);

    if (
      !premium ||
      isLoading(currentPremiumStatus) ||
      (currentPremiumStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    setStatus(newStatus, premiumSection, status, commit);

    await Promise.all([
      dispatch('fetchDSRHistory', refresh),
      dispatch('fetchAaveHistory', { refresh }),
      dispatch('fetchCompoundHistory', refresh),
      dispatch('fetchYearnVaultsHistory', {
        refresh,
        version: ProtocolVersion.V1
      }),
      dispatch('fetchYearnVaultsHistory', {
        refresh,
        version: ProtocolVersion.V2
      })
    ]);

    setStatus(Status.LOADED, premiumSection, status, commit);
  },

  async resetDB(
    { commit, dispatch, rootState: { session }, rootGetters: { status } },
    protocols: DefiProtocol[]
  ) {
    const premiumSection = Section.DEFI_LENDING_HISTORY;
    const currentPremiumStatus = status(premiumSection);
    const premium = session!.premium;

    if (!premium || isLoading(currentPremiumStatus)) {
      return;
    }

    setStatus(Status.REFRESHING, premiumSection, status, commit);

    const toReset: Promise<void>[] = [];
    if (protocols.includes(DefiProtocol.YEARN_VAULTS)) {
      toReset.push(
        dispatch('fetchYearnVaultsHistory', {
          refresh: true,
          reset: true,
          version: ProtocolVersion.V1
        })
      );
    }

    if (protocols.includes(DefiProtocol.YEARN_VAULTS_V2)) {
      toReset.push(
        dispatch('fetchYearnVaultsHistory', {
          refresh: true,
          reset: true,
          version: ProtocolVersion.V2
        })
      );
    }

    if (protocols.includes(DefiProtocol.AAVE)) {
      toReset.push(
        dispatch('fetchAaveHistory', { refresh: true, reset: true })
      );
    }

    await Promise.all(toReset);

    setStatus(Status.LOADED, premiumSection, status, commit);
  },

  async fetchBorrowing(
    { commit, dispatch, rootState: { session }, rootGetters: { status } },
    refresh: boolean = false
  ) {
    const premium = session?.premium;
    const section = Section.DEFI_BORROWING;
    const premiumSection = Section.DEFI_BORROWING_HISTORY;
    const currentStatus = status(section);
    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;

    if (
      !isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && refresh)
    ) {
      setStatus(newStatus, section, status, commit);
      await Promise.all([
        dispatch('fetchMakerDAOVaults', refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED, section, status, commit);
        }),
        dispatch('fetchCompoundBalances', refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED, section, status, commit);
        }),
        dispatch('fetchAaveBalances', refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED, section, status, commit);
        }),
        dispatch('liquity/fetchBalances', refresh).then(() => {
          setStatus(Status.PARTIALLY_LOADED, section, status, commit);
        })
      ]);

      setStatus(Status.LOADED, section, status, commit);
    }

    const currentPremiumStatus = status(premiumSection);

    if (
      !premium ||
      isLoading(currentPremiumStatus) ||
      (currentPremiumStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    setStatus(newStatus, premiumSection, status, commit);

    await Promise.all([
      dispatch('fetchMakerDAOVaultDetails', refresh),
      dispatch('fetchCompoundHistory', refresh),
      dispatch('fetchAaveHistory', refresh),
      dispatch('liquity/fetchEvents', refresh)
    ]);

    setStatus(Status.LOADED, premiumSection, status, commit);
  },

  async fetchCompoundBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.COMPOUND)) {
      return;
    }

    const section = Section.DEFI_COMPOUND_BALANCES;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);

    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.DEFI_COMPOUND_BALANCES;
      const { taskId } = await api.defi.fetchCompoundBalances();
      const { result } = await awaitTask<CompoundBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.compound.task.title'),
          numericKeys: balanceKeys
        }
      );
      commit('compoundBalances', result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.tc('actions.defi.compound.error.title'),
        message: i18n.tc('actions.defi.compound.error.description', undefined, {
          error: e.message
        }),
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchCompoundHistory(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;

    if (!activeModules.includes(Module.COMPOUND) || !session?.premium) {
      return;
    }

    const section = Section.DEFI_COMPOUND_HISTORY;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);

    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.DEFI_COMPOUND_HISTORY;
      const { taskId } = await api.defi.fetchCompoundHistory();
      const { result } = await awaitTask<CompoundHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.compound_history.task.title'),
          numericKeys: balanceKeys
        }
      );

      commit('compoundHistory', result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.tc('actions.defi.compound_history.error.title'),
        message: i18n.tc(
          'actions.defi.compound_history.error.description',
          undefined,
          {
            error: e.message
          }
        ),
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchYearnVaultBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    { refresh, version }: { refresh: boolean; version: ProtocolVersion } = {
      refresh: false,
      version: ProtocolVersion.V1
    }
  ) {
    const { activeModules } = session!.generalSettings;
    const isV1 = version === ProtocolVersion.V1;
    const isV2 = version === ProtocolVersion.V2;
    const isYearnV1AndActive = activeModules.includes(Module.YEARN) && isV1;
    const isYearnV2AndActive = activeModules.includes(Module.YEARN_V2) && isV2;
    const isModuleActive = isYearnV1AndActive || isYearnV2AndActive;

    if (!isModuleActive) {
      return;
    }

    const section = isV1
      ? Section.DEFI_YEARN_VAULTS_BALANCES
      : Section.DEFI_YEARN_VAULTS_V2_BALANCES;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();
    try {
      const taskType = isV1
        ? TaskType.DEFI_YEARN_VAULT_BALANCES
        : TaskType.DEFI_YEARN_VAULT_V2_BALANCES;
      const { taskId } = await api.defi.fetchYearnVaultsBalances(version);
      const { result } = await awaitTask<YearnVaultsBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n
            .t('actions.defi.yearn_vaults.task.title', { version })
            .toString(),
          numericKeys: balanceKeys
        }
      );

      commit(
        isV1
          ? DefiMutations.YEARN_VAULTS_BALANCES
          : DefiMutations.YEARN_VAULTS_V2_BALANCES,
        result
      );
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n
          .t('actions.defi.yearn_vaults.error.title', { version })
          .toString(),
        message: i18n
          .t('actions.defi.yearn_vaults.error.description', {
            error: e.message,
            version
          })
          .toString(),
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchYearnVaultsHistory(
    { commit, rootGetters: { status }, rootState: { session } },
    payload: { refresh?: boolean; reset?: boolean; version: ProtocolVersion }
  ) {
    const refresh = payload?.refresh;
    const reset = payload?.reset;
    const { activeModules } = session!.generalSettings;

    const isV1 = payload.version === ProtocolVersion.V1;
    const isV2 = payload.version === ProtocolVersion.V2;
    const isYearnV1AndActive = activeModules.includes(Module.YEARN) && isV1;
    const isYearnV2AndActive = activeModules.includes(Module.YEARN_V2) && isV2;
    const isModuleActive = isYearnV1AndActive || isYearnV2AndActive;

    if (!isModuleActive || !session?.premium) {
      return;
    }

    const section = isV1
      ? Section.DEFI_YEARN_VAULTS_HISTORY
      : Section.DEFI_YEARN_VAULTS_V2_HISTORY;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();
    try {
      const taskType = isV1
        ? TaskType.DEFI_YEARN_VAULT_HISTORY
        : TaskType.DEFI_YEARN_VAULT_V2_HISTORY;
      const { taskId } = await api.defi.fetchYearnVaultsHistory(
        payload.version,
        reset
      );
      const { result } = await awaitTask<YearnVaultsHistory, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n
            .t('actions.defi.yearn_vaults_history.task.title', {
              version: payload.version
            })
            .toString(),
          numericKeys: balanceKeys
        }
      );

      commit(
        isV1
          ? DefiMutations.YEARN_VAULTS_HISTORY
          : DefiMutations.YEARN_VAULTS_V2_HISTORY,
        result
      );
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n
          .t('actions.defi.yearn_vaults_history.error.title', {
            version: payload.version
          })
          .toString(),
        message: i18n
          .t('actions.defi.yearn_vaults_history.error.description', {
            error: e.message,
            version: payload.version
          })
          .toString(),
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchUniswapBalances(
    { dispatch, commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.UNISWAP)) {
      return;
    }

    const section = Section.DEFI_UNISWAP_BALANCES;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.DEFI_UNISWAP_BALANCES;
      const { taskId } = await api.defi.fetchUniswapBalances();
      const { result } = await awaitTask<XswapBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.uniswap.task.title'),
          numericKeys: uniswapNumericKeys
        }
      );

      commit('uniswapBalances', result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.tc('actions.defi.uniswap.error.title'),
        message: i18n.tc('actions.defi.uniswap.error.description', undefined, {
          error: e.message
        }),
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
    await dispatch('balances/fetchSupportedAssets', true, { root: true });
  },

  async fetchUniswapTrades(
    { dispatch, commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.UNISWAP) || !session!.premium) {
      return;
    }

    const section = Section.DEFI_UNISWAP_TRADES;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.DEFI_UNISWAP_TRADES;
      const { taskId } = await api.defi.fetchUniswapTrades();
      const { result } = await awaitTask<DexTrades, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.uniswap_trades.task.title'),
          numericKeys: dexTradeNumericKeys
        }
      );

      commit('uniswapTrades', result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.tc('actions.defi.uniswap_trades.error.title'),
        message: i18n.tc(
          'actions.defi.uniswap_trades.error.description',
          undefined,
          {
            error: e.message
          }
        ),
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
    await dispatch('balances/fetchSupportedAssets', true, { root: true });
  },

  async fetchUniswapEvents(
    { dispatch, commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.UNISWAP) || !session!.premium) {
      return;
    }

    const section = Section.DEFI_UNISWAP_EVENTS;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);

    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.DEFI_UNISWAP_EVENTS;
      const { taskId } = await api.defi.fetchUniswapEvents();
      const { result } = await awaitTask<XswapEvents, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.defi.uniswap_events.task.title'),
          numericKeys: uniswapEventsNumericKeys
        }
      );

      commit('uniswapEvents', result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.tc('actions.defi.uniswap_events.error.title'),
        message: i18n.tc(
          'actions.defi.uniswap_events.error.description',
          undefined,
          {
            error: e.message
          }
        ),
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
    await dispatch('balances/fetchSupportedAssets', true, { root: true });
  },

  async fetchAirdrops(
    { commit, rootGetters: { status } },
    refresh: boolean = false
  ) {
    const section = Section.DEFI_AIRDROPS;
    const currentStatus = status(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);
    const { awaitTask } = useTasks();

    try {
      const { taskId } = await api.airdrops();
      const { result } = await awaitTask<Airdrops, TaskMeta>(
        taskId,
        TaskType.DEFI_AIRDROPS,
        {
          title: i18n.t('actions.defi.airdrops.task.title').toString(),
          numericKeys: balanceKeys
        }
      );

      commit('airdrops', result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.defi.airdrops.error.title').toString(),
        message: i18n
          .t('actions.defi.airdrops.error.description', {
            error: e.message
          })
          .toString(),
        display: true
      });
    }
    setStatus(Status.LOADED, section, status, commit);
  },
  async fetchBalancerBalances(
    context: ActionContext<DefiState, RotkehlchenState>,
    refresh: boolean = false
  ) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.balancer_balances.task.title').toString(),
      numericKeys: [...balanceKeys, 'total_amount', 'usd_price']
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchBalancerBalances(),
      mutation: 'balancerBalances',
      taskType: TaskType.BALANCER_BALANCES,
      section: Section.DEFI_BALANCER_BALANCES,
      module: Module.BALANCER,
      meta: meta,
      refresh,
      checkPremium: true,
      onError: {
        title: i18n.t('actions.defi.balancer_balances.error.title').toString(),
        error: message =>
          i18n
            .t('actions.defi.balancer_balances.error.description', {
              message
            })
            .toString()
      }
    });
    await context.dispatch('balances/fetchSupportedAssets', true, {
      root: true
    });
  },
  async fetchBalancerTrades(
    context: ActionContext<DefiState, RotkehlchenState>,
    refresh: boolean = false
  ) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.balancer_trades.task.title').toString(),
      numericKeys: dexTradeNumericKeys
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchBalancerTrades(),
      mutation: 'balancerTrades',
      taskType: TaskType.BALANCER_TRADES,
      section: Section.DEFI_BALANCER_TRADES,
      module: Module.BALANCER,
      meta: meta,
      checkPremium: true,
      refresh,
      onError: {
        title: i18n.t('actions.defi.balancer_trades.error.title').toString(),
        error: message =>
          i18n
            .t('actions.defi.balancer_trades.error.description', {
              message
            })
            .toString()
      }
    });
    await context.dispatch('balances/fetchSupportedAssets', true, {
      root: true
    });
  },
  async fetchBalancerEvents(
    context: ActionContext<DefiState, RotkehlchenState>,
    refresh: boolean = false
  ) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.balancer_events.task.title').toString(),
      numericKeys: [
        ...balanceKeys,
        'amounts',
        'profit_loss_amounts',
        'usd_profit_loss'
      ]
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchBalancerEvents(),
      mutation: 'balancerEvents',
      taskType: TaskType.BALANCER_EVENT,
      section: Section.DEFI_BALANCER_EVENTS,
      module: Module.BALANCER,
      meta: meta,
      checkPremium: true,
      refresh,
      onError: {
        title: i18n.t('actions.defi.balancer_events.error.title').toString(),
        error: message =>
          i18n
            .t('actions.defi.balancer_events.error.description', {
              message
            })
            .toString()
      }
    });
    await context.dispatch('balances/fetchSupportedAssets', true, {
      root: true
    });
  },
  async [ACTION_PURGE_PROTOCOL](
    { commit, rootGetters: { status }, dispatch },
    module: Module | typeof ALL_MODULES
  ) {
    function resetStatus(section: Section) {
      setStatus(Status.NONE, section, status, commit);
    }

    function clearDSRState() {
      commit('dsrBalances', {
        currentDsr: Zero,
        balances: {}
      } as DSRBalances);
      commit('dsrHistory', {});
      resetStatus(Section.DEFI_DSR_BALANCES);
      resetStatus(Section.DEFI_DSR_HISTORY);
    }

    function clearMakerDAOVaultState() {
      commit('makerDAOVaults', []);
      commit('makerDAOVaultDetails', []);
      resetStatus(Section.DEFI_MAKERDAO_VAULTS);
      resetStatus(Section.DEFI_MAKERDAO_VAULT_DETAILS);
    }

    function clearAaveState() {
      commit('aaveBalances', {});
      commit('aaveHistory', {});
      resetStatus(Section.DEFI_AAVE_BALANCES);
      resetStatus(Section.DEFI_AAVE_HISTORY);
    }

    function clearCompoundState() {
      commit('compoundBalances', {});
      commit('compoundHistory', defaultCompoundHistory());
      resetStatus(Section.DEFI_COMPOUND_BALANCES);
      resetStatus(Section.DEFI_COMPOUND_HISTORY);
    }

    function clearYearnVaultsState() {
      commit(DefiMutations.YEARN_VAULTS_BALANCES, {});
      commit(DefiMutations.YEARN_VAULTS_HISTORY, {});

      resetStatus(Section.DEFI_YEARN_VAULTS_BALANCES);
      resetStatus(Section.DEFI_YEARN_VAULTS_HISTORY);
    }

    function clearYearnVaultsV2State() {
      commit(DefiMutations.YEARN_VAULTS_V2_BALANCES, {});
      commit(DefiMutations.YEARN_VAULTS_V2_HISTORY, {});

      resetStatus(Section.DEFI_YEARN_VAULTS_V2_BALANCES);
      resetStatus(Section.DEFI_YEARN_VAULTS_V2_HISTORY);
    }

    function clearUniswapState() {
      commit('uniswapBalances', {});
      commit('uniswapTrades', {});
      commit('uniswapEvents', {});

      resetStatus(Section.DEFI_UNISWAP_BALANCES);
      resetStatus(Section.DEFI_UNISWAP_TRADES);
      resetStatus(Section.DEFI_UNISWAP_EVENTS);
    }

    function clearBalancerState() {
      commit('balancerBalances', {});
      commit('balancerTrades', {});
      commit('balancerEvents', {});

      resetStatus(Section.DEFI_BALANCER_BALANCES);
      resetStatus(Section.DEFI_BALANCER_TRADES);
      resetStatus(Section.DEFI_BALANCER_EVENTS);
    }

    if (module === Module.MAKERDAO_DSR) {
      clearDSRState();
    } else if (module === Module.MAKERDAO_VAULTS) {
      clearMakerDAOVaultState();
    } else if (module === Module.AAVE) {
      clearAaveState();
    } else if (module === Module.COMPOUND) {
      clearCompoundState();
    } else if (module === Module.YEARN) {
      clearYearnVaultsState();
    } else if (module === Module.YEARN_V2) {
      clearYearnVaultsV2State();
    } else if (module === Module.UNISWAP) {
      clearUniswapState();
    } else if (module === Module.BALANCER) {
      clearBalancerState();
    } else if (Module.SUSHISWAP) {
      dispatch('sushiswap/purge');
    } else if (module === ALL_MODULES) {
      clearDSRState();
      clearMakerDAOVaultState();
      clearAaveState();
      clearCompoundState();
      clearYearnVaultsState();
      clearYearnVaultsV2State();
      clearUniswapState();
      clearBalancerState();
    }
  }
};
