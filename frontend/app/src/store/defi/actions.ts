import { ActionContext, ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { balanceKeys } from '@/services/consts';
import {
  aaveHistoryKeys,
  DEFI_AAVE,
  DEFI_YEARN_VAULTS,
  DEFI_YEARN_VAULTS_V2,
  dsrKeys,
  V1,
  V2,
  vaultDetailsKeys,
  vaultKeys
} from '@/services/defi/consts';
import {
  ApiMakerDAOVault,
  ProtocolVersion,
  SupportedDefiProtocols
} from '@/services/defi/types';
import { AaveBalances, AaveHistory } from '@/services/defi/types/aave';
import {
  CompoundBalances,
  CompoundHistory
} from '@/services/defi/types/compound';
import { UniswapBalances } from '@/services/defi/types/uniswap';
import {
  YearnVaultsBalances,
  YearnVaultsHistory
} from '@/services/defi/types/yearn';
import { api } from '@/services/rotkehlchen-api';
import {
  ALL_MODULES,
  MODULE_AAVE,
  MODULE_BALANCER,
  MODULE_COMPOUND,
  MODULE_MAKERDAO_DSR,
  MODULE_MAKERDAO_VAULTS,
  MODULE_UNISWAP,
  MODULE_YEARN,
  MODULE_YEARN_V2
} from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';
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
  MakerDAOVaultDetails,
  UniswapEvents
} from '@/store/defi/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/types';
import { fetchAsync, isLoading, setStatus } from '@/store/utils';
import { Zero } from '@/utils/bignumbers';

export const actions: ActionTree<DefiState, RotkehlchenState> = {
  async fetchDSRBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_MAKERDAO_DSR)) {
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

    try {
      const taskType = TaskType.DSR_BALANCE;
      const { taskId } = await api.defi.dsrBalance();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.dsr_balances.task.title'),
        ignoreResult: false,
        numericKeys: dsrKeys
      });
      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<DSRBalances, TaskMeta>(taskType);
      commit('dsrBalances', result);
    } catch (e) {
      const message = i18n.tc(
        'actions.defi.dsr_balances.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = i18n.tc('actions.defi.dsr_balances.error.title');
      notify(message, title, Severity.ERROR, true);
    }

    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchDSRHistory(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_MAKERDAO_DSR) || !session?.premium) {
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

    try {
      const taskType = TaskType.DSR_HISTORY;
      const { taskId } = await api.defi.dsrHistory();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.dsr_history.task.title'),
        ignoreResult: false,
        numericKeys: balanceKeys
      });
      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<DSRHistory, TaskMeta>(taskType);
      commit('dsrHistory', result);
    } catch (e) {
      const message = i18n.tc(
        'actions.defi.dsr_history.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = i18n.tc('actions.defi.dsr_history.error.title');
      notify(message, title, Severity.ERROR, true);
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchMakerDAOVaults(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_MAKERDAO_VAULTS)) {
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

    try {
      const taskType = TaskType.MAKEDAO_VAULTS;
      const { taskId } = await api.defi.makerDAOVaults();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.makerdao_vaults.task.title'),
        ignoreResult: false,
        numericKeys: vaultKeys
      });

      commit('tasks/add', task, { root: true });

      const { result: makerDAOVaults } = await taskCompletion<
        ApiMakerDAOVault[],
        TaskMeta
      >(taskType);
      commit('makerDAOVaults', convertMakerDAOVaults(makerDAOVaults));
    } catch (e) {
      const message = i18n.tc(
        'actions.defi.makerdao_vaults.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = i18n.tc('actions.defi.makerdao_vaults.error.title');
      notify(message, title, Severity.ERROR, true);
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchMakerDAOVaultDetails(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_MAKERDAO_VAULTS) || !session?.premium) {
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

    try {
      const { taskId } = await api.defi.makerDAOVaultDetails();
      const task = createTask(taskId, TaskType.MAKERDAO_VAULT_DETAILS, {
        title: i18n.tc('actions.defi.makerdao_vault_details.task.title'),
        ignoreResult: false,
        numericKeys: vaultDetailsKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<MakerDAOVaultDetails[], TaskMeta>(
        TaskType.MAKERDAO_VAULT_DETAILS
      );

      commit('makerDAOVaultDetails', result);
    } catch (e) {
      const message = i18n.tc(
        'actions.defi.makerdao_vault_details.error.description',
        undefined,
        { error: e.message }
      );
      const title = i18n.tc('actions.defi.makerdao_vault_details.error.title');
      notify(message, title, Severity.ERROR, true);
    }

    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchAaveBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_AAVE)) {
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

    try {
      const taskType = TaskType.AAVE_BALANCES;
      const { taskId } = await api.defi.fetchAaveBalances();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.aave_balances.task.title'),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<AaveBalances, TaskMeta>(taskType);

      commit('aaveBalances', result);
    } catch (e) {
      const message = i18n.tc(
        'actions.defi.aave_balances.error.description',
        undefined,
        {
          error: e.message
        }
      );
      const title = i18n.tc('actions.defi.aave_balances.error.title');
      notify(message, title, Severity.ERROR, true);
    }

    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchAaveHistory(
    { commit, rootGetters: { status }, rootState: { session } },
    payload: { refresh?: boolean; reset?: boolean }
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_AAVE) || !session?.premium) {
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

    try {
      const taskType = TaskType.AAVE_HISTORY;
      const { taskId } = await api.defi.fetchAaveHistory(reset);
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.aave_history.task.title'),
        ignoreResult: false,
        numericKeys: aaveHistoryKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<AaveHistory, TaskMeta>(taskType);

      commit('aaveHistory', result);
    } catch (e) {
      const message = i18n.tc(
        'actions.defi.aave_history.error.description',
        undefined,
        { error: e.message }
      );
      const title = i18n.tc('actions.defi.aave_history.error.title');
      notify(message, title, Severity.ERROR, true);
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

    try {
      const taskType = TaskType.DEFI_BALANCES;
      const { taskId } = await api.defi.fetchAllDefi();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.balances.task.title'),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<AllDefiProtocols, TaskMeta>(
        taskType
      );

      commit('allDefiProtocols', result);
    } catch (e) {
      const title = i18n.tc('actions.defi.balances.error.title');
      const message = i18n.tc(
        'actions.defi.balances.error.description',
        undefined,
        { error: e.message }
      );
      notify(message, title, Severity.ERROR, true);
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
      dispatch('fetchYearnVaultBalances', { refresh, version: V1 }),
      dispatch('fetchYearnVaultBalances', { refresh, version: V2 })
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
        dispatch('fetchYearnVaultBalances', { refresh, version: V1 }).then(
          () => {
            setStatus(Status.PARTIALLY_LOADED, section, status, commit);
          }
        ),
        dispatch('fetchYearnVaultBalances', { refresh, version: V2 }).then(
          () => {
            setStatus(Status.PARTIALLY_LOADED, section, status, commit);
          }
        )
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
      dispatch('fetchYearnVaultsHistory', { refresh, version: V1 }),
      dispatch('fetchYearnVaultsHistory', { refresh, version: V2 })
    ]);

    setStatus(Status.LOADED, premiumSection, status, commit);
  },

  async resetDB(
    { commit, dispatch, rootState: { session }, rootGetters: { status } },
    protocols: SupportedDefiProtocols[]
  ) {
    const premiumSection = Section.DEFI_LENDING_HISTORY;
    const currentPremiumStatus = status(premiumSection);
    const premium = session!.premium;

    if (!premium || isLoading(currentPremiumStatus)) {
      return;
    }

    setStatus(Status.REFRESHING, premiumSection, status, commit);

    const toReset: Promise<void>[] = [];
    if (protocols.includes(DEFI_YEARN_VAULTS)) {
      toReset.push(
        dispatch('fetchYearnVaultsHistory', {
          refresh: true,
          reset: true,
          version: V1
        })
      );
    }

    if (protocols.includes(DEFI_YEARN_VAULTS_V2)) {
      toReset.push(
        dispatch('fetchYearnVaultsHistory', {
          refresh: true,
          reset: true,
          version: V2
        })
      );
    }

    if (protocols.includes(DEFI_AAVE)) {
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
      dispatch('fetchAaveHistory', refresh)
    ]);

    setStatus(Status.LOADED, premiumSection, status, commit);
  },

  async fetchCompoundBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_COMPOUND)) {
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

    try {
      const taskType = TaskType.DEFI_COMPOUND_BALANCES;
      const { taskId } = await api.defi.fetchCompoundBalances();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.compound.task.title'),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<CompoundBalances, TaskMeta>(
        taskType
      );

      commit('compoundBalances', result);
    } catch (e) {
      notify(
        i18n.tc('actions.defi.compound.error.description', undefined, {
          error: e.message
        }),
        i18n.tc('actions.defi.compound.error.title'),
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchCompoundHistory(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;

    if (!activeModules.includes(MODULE_COMPOUND) || !session?.premium) {
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

    try {
      const taskType = TaskType.DEFI_COMPOUND_HISTORY;
      const { taskId } = await api.defi.fetchCompoundHistory();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.compound_history.task.title'),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<CompoundHistory, TaskMeta>(
        taskType
      );

      commit('compoundHistory', result);
    } catch (e) {
      notify(
        i18n.tc('actions.defi.compound_history.error.description', undefined, {
          error: e.message
        }),
        i18n.tc('actions.defi.compound_history.error.title'),
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchYearnVaultBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    { refresh, version }: { refresh: boolean; version: ProtocolVersion } = {
      refresh: false,
      version: V1
    }
  ) {
    const { activeModules } = session!.generalSettings;
    const isV1 = version === V1;
    const isV2 = version === V2;
    const isYearnV1AndActive = activeModules.includes(MODULE_YEARN) && isV1;
    const isYearnV2AndActive = activeModules.includes(MODULE_YEARN_V2) && isV2;
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

    try {
      const taskType = isV1
        ? TaskType.DEFI_YEARN_VAULT_BALANCES
        : TaskType.DEFI_YEARN_VAULT_V2_BALANCES;
      const { taskId } = await api.defi.fetchYearnVaultsBalances(version);
      const task = createTask(taskId, taskType, {
        title: i18n
          .t('actions.defi.yearn_vaults.task.title', { version })
          .toString(),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<YearnVaultsBalances, TaskMeta>(
        taskType
      );

      commit(
        isV1
          ? DefiMutations.YEARN_VAULTS_BALANCES
          : DefiMutations.YEARN_VAULTS_V2_BALANCES,
        result
      );
    } catch (e) {
      notify(
        i18n
          .t('actions.defi.yearn_vaults.error.description', {
            error: e.message,
            version
          })
          .toString(),
        i18n.t('actions.defi.yearn_vaults.error.title', { version }).toString(),
        Severity.ERROR,
        true
      );
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

    const isV1 = payload.version === V1;
    const isV2 = payload.version === V2;
    const isYearnV1AndActive = activeModules.includes(MODULE_YEARN) && isV1;
    const isYearnV2AndActive = activeModules.includes(MODULE_YEARN_V2) && isV2;
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

    try {
      const taskType = isV1
        ? TaskType.DEFI_YEARN_VAULT_HISTORY
        : TaskType.DEFI_YEARN_VAULT_V2_HISTORY;
      const { taskId } = await api.defi.fetchYearnVaultsHistory(
        payload.version,
        reset
      );
      const task = createTask(taskId, taskType, {
        title: i18n
          .t('actions.defi.yearn_vaults_history.task.title', {
            version: payload.version
          })
          .toString(),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<YearnVaultsHistory, TaskMeta>(
        taskType
      );

      commit(
        isV1
          ? DefiMutations.YEARN_VAULTS_HISTORY
          : DefiMutations.YEARN_VAULTS_V2_HISTORY,
        result
      );
    } catch (e) {
      notify(
        i18n
          .t('actions.defi.yearn_vaults_history.error.description', {
            error: e.message,
            version: payload.version
          })
          .toString(),
        i18n
          .t('actions.defi.yearn_vaults_history.error.title', {
            version: payload.version
          })
          .toString(),
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchUniswapBalances(
    { dispatch, commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_UNISWAP)) {
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

    try {
      const taskType = TaskType.DEFI_UNISWAP_BALANCES;
      const { taskId } = await api.defi.fetchUniswapBalances();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.uniswap.task.title'),
        ignoreResult: false,
        numericKeys: uniswapNumericKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<UniswapBalances, TaskMeta>(
        taskType
      );

      commit('uniswapBalances', result);
    } catch (e) {
      notify(
        i18n.tc('actions.defi.uniswap.error.description', undefined, {
          error: e.message
        }),
        i18n.tc('actions.defi.uniswap.error.title'),
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);
    await dispatch('balances/fetchSupportedAssets', true, { root: true });
  },

  async fetchUniswapTrades(
    { dispatch, commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_UNISWAP) || !session!.premium) {
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

    try {
      const taskType = TaskType.DEFI_UNISWAP_TRADES;
      const { taskId } = await api.defi.fetchUniswapTrades();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.uniswap_trades.task.title'),
        ignoreResult: false,
        numericKeys: dexTradeNumericKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<DexTrades, TaskMeta>(taskType);

      commit('uniswapTrades', result);
    } catch (e) {
      notify(
        i18n.tc('actions.defi.uniswap_trades.error.description', undefined, {
          error: e.message
        }),
        i18n.tc('actions.defi.uniswap_trades.error.title'),
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);
    await dispatch('balances/fetchSupportedAssets', true, { root: true });
  },

  async fetchUniswapEvents(
    { dispatch, commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_UNISWAP) || !session!.premium) {
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

    try {
      const taskType = TaskType.DEFI_UNISWAP_EVENTS;
      const { taskId } = await api.defi.fetchUniswapEvents();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.uniswap_events.task.title'),
        ignoreResult: false,
        numericKeys: uniswapEventsNumericKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<UniswapEvents, TaskMeta>(
        taskType
      );

      commit('uniswapEvents', result);
    } catch (e) {
      notify(
        i18n.tc('actions.defi.uniswap_events.error.description', undefined, {
          error: e.message
        }),
        i18n.tc('actions.defi.uniswap_events.error.title'),
        Severity.ERROR,
        true
      );
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

    try {
      const taskType = TaskType.DEFI_AIRDROPS;
      const { taskId } = await api.airdrops();
      const task = createTask(taskId, taskType, {
        title: i18n.t('actions.defi.airdrops.task.title').toString(),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<Airdrops, TaskMeta>(taskType);

      commit('airdrops', result);
    } catch (e) {
      notify(
        i18n
          .t('actions.defi.airdrops.error.description', {
            error: e.message
          })
          .toString(),
        i18n.t('actions.defi.airdrops.error.title').toString(),
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);
  },
  async fetchBalancerBalances(
    context: ActionContext<DefiState, RotkehlchenState>,
    refresh: boolean = false
  ) {
    const meta: TaskMeta = {
      title: i18n.t('actions.defi.balancer_balances.task.title').toString(),
      ignoreResult: false,
      numericKeys: [...balanceKeys, 'total_amount', 'usd_price']
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchBalancerBalances(),
      mutation: 'balancerBalances',
      taskType: TaskType.BALANCER_BALANCES,
      section: Section.DEFI_BALANCER_BALANCES,
      module: MODULE_BALANCER,
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
      ignoreResult: false,
      numericKeys: dexTradeNumericKeys
    };

    await fetchAsync(context, {
      query: async () => await api.defi.fetchBalancerTrades(),
      mutation: 'balancerTrades',
      taskType: TaskType.BALANCER_TRADES,
      section: Section.DEFI_BALANCER_TRADES,
      module: MODULE_BALANCER,
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
      ignoreResult: false,
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
      module: MODULE_BALANCER,
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
    { commit, rootGetters: { status } },
    module: SupportedModules | typeof ALL_MODULES
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

    if (module === MODULE_MAKERDAO_DSR) {
      clearDSRState();
    } else if (module === MODULE_MAKERDAO_VAULTS) {
      clearMakerDAOVaultState();
    } else if (module === MODULE_AAVE) {
      clearAaveState();
    } else if (module === MODULE_COMPOUND) {
      clearCompoundState();
    } else if (module === MODULE_YEARN) {
      clearYearnVaultsState();
    } else if (module === MODULE_YEARN_V2) {
      clearYearnVaultsV2State();
    } else if (module === MODULE_UNISWAP) {
      clearUniswapState();
    } else if (module === MODULE_BALANCER) {
      clearBalancerState();
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
