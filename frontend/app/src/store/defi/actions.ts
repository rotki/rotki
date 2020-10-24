import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import { balanceKeys } from '@/services/consts';
import {
  aaveHistoryKeys,
  DEFI_AAVE,
  DEFI_YEARN_VAULTS,
  dsrKeys,
  vaultDetailsKeys,
  vaultKeys
} from '@/services/defi/consts';
import {
  ApiMakerDAOVault,
  SupportedDefiProtocols
} from '@/services/defi/types';
import { AaveBalances, AaveHistory } from '@/services/defi/types/aave';
import {
  CompoundBalances,
  CompoundHistory
} from '@/services/defi/types/compound';
import {
  YearnVaultsBalances,
  YearnVaultsHistory
} from '@/services/defi/types/yearn';
import { api } from '@/services/rotkehlchen-api';
import { MODULE_YEARN } from '@/services/session/consts';
import { Section, Status } from '@/store/const';
import { convertMakerDAOVaults } from '@/store/defi/converters';
import {
  AllDefiProtocols,
  DefiState,
  DSRBalances,
  DSRHistory,
  MakerDAOVaultDetails
} from '@/store/defi/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/types';
import { setStatus } from '@/store/utils';

function isLoading(status: Status): boolean {
  return (
    status === Status.LOADING ||
    status === Status.PARTIALLY_LOADED ||
    status == Status.REFRESHING
  );
}

export const actions: ActionTree<DefiState, RotkehlchenState> = {
  async fetchDSRBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes('makerdao_dsr')) {
      return;
    }
    const section = Section.DEFI_DRS_BALANCES;
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
    if (!activeModules.includes('makerdao_dsr') || !session?.premium) {
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
    if (!activeModules.includes('makerdao_vaults')) {
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
    if (!activeModules.includes('makerdao_vaults') || !session?.premium) {
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
    if (!activeModules.includes('aave')) {
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
    if (!activeModules.includes('aave') || !session?.premium) {
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
      dispatch('fetchYearnVaultBalances', refresh)
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
        dispatch('fetchYearnVaultBalances', refresh).then(() => {
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
      dispatch('fetchYearnVaultsHistory', { refresh })
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
        dispatch('fetchYearnVaultsHistory', { refresh: true, reset: true })
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
    if (!activeModules.includes('compound')) {
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

    if (!activeModules.includes('compound') || !session?.premium) {
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
    refresh: boolean = false
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(DEFI_YEARN_VAULTS)) {
      return;
    }

    const section = Section.DEFI_YEARN_VAULTS_BALANCES;
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
      const taskType = TaskType.DEFI_YEARN_VAULT_BALANCES;
      const { taskId } = await api.defi.fetchYearnVaultsBalances();
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.yearn_vaults.task.title'),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<YearnVaultsBalances, TaskMeta>(
        taskType
      );

      commit('yearnVaultsBalances', result);
    } catch (e) {
      notify(
        i18n.tc('actions.defi.yearn_vaults.error.description', undefined, {
          error: e.message
        }),
        i18n.tc('actions.defi.yearn_vaults.error.title'),
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchYearnVaultsHistory(
    { commit, rootGetters: { status }, rootState: { session } },
    payload: { refresh?: boolean; reset?: boolean }
  ) {
    const refresh = payload?.refresh;
    const reset = payload?.reset;
    const { activeModules } = session!.generalSettings;

    if (!activeModules.includes(MODULE_YEARN) || !session?.premium) {
      return;
    }

    const section = Section.DEFI_YEARN_VAULTS_HISTORY;
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
      const taskType = TaskType.DEFI_YEARN_VAULT_HISTORY;
      const { taskId } = await api.defi.fetchYearnVaultsHistory(reset);
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.defi.yearn_vaults_history.task.title'),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<YearnVaultsHistory, TaskMeta>(
        taskType
      );

      commit('yearnVaultsHistory', result);
    } catch (e) {
      notify(
        i18n.tc(
          'actions.defi.yearn_vaults_history.error.description',
          undefined,
          {
            error: e.message
          }
        ),
        i18n.tc('actions.defi.yearn_vaults_history.error.title'),
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);
  }
};
