import { ActionTree } from 'vuex';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import {
  ApiAaveBalances,
  ApiAaveHistory,
  ApiAllDefiProtocols,
  ApiDSRBalances,
  ApiDSRHistory,
  ApiMakerDAOVault,
  ApiMakerDAOVaultDetails
} from '@/services/defi/types';
import { api } from '@/services/rotkehlchen-api';
import {
  convertAaveBalances,
  convertAaveHistory,
  convertAllDefiProtocols,
  convertDSRBalances,
  convertDSRHistory,
  convertMakerDAOVaults,
  convertVaultDetails
} from '@/store/defi/converters';
import { Status } from '@/store/defi/status';
import { DefiState } from '@/store/defi/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { Message, RotkehlchenState } from '@/store/store';

export const actions: ActionTree<DefiState, RotkehlchenState> = {
  async fetchDSRBalances({
    commit,
    rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
  }) {
    const taskType = TaskType.DSR_BALANCE;
    if (isTaskRunning(taskType)) {
      return;
    }

    try {
      const { task_id } = await api.defi.dsrBalance();
      const task = createTask(task_id, taskType, {
        description: `Fetching DSR Balances`,
        ignoreResult: false
      });
      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<ApiDSRBalances, TaskMeta>(
        taskType
      );
      commit('dsrBalances', convertDSRBalances(result));
    } catch (e) {
      notify(
        `There was an issue while fetching DSR Balances: ${e.message}`,
        'DSR Balances',
        Severity.ERROR
      );
    }
  },

  async fetchDSRHistory({
    commit,
    rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
  }) {
    const taskType = TaskType.DSR_HISTORY;

    if (isTaskRunning(taskType)) {
      return;
    }

    try {
      const { task_id } = await api.defi.dsrHistory();
      const task = createTask(task_id, taskType, {
        description: `Fetching DSR History`,
        ignoreResult: false
      });
      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<ApiDSRHistory, TaskMeta>(
        taskType
      );
      commit('dsrHistory', convertDSRHistory(result));
    } catch (e) {
      notify(
        `There was an issue while fetching DSR History: ${e.message}`,
        'DSR History',
        Severity.ERROR
      );
    }
  },

  async fetchMakerDAOVaults({
    commit,
    rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
  }) {
    const taskType = TaskType.MAKEDAO_VAULTS;
    if (isTaskRunning(taskType)) {
      return;
    }

    try {
      const { task_id } = await api.defi.makerDAOVaults();
      const task = createTask(task_id, taskType, {
        description: `Fetching MakerDAO Vaults`,
        ignoreResult: false
      });

      commit('tasks/add', task, { root: true });

      const { result: makerDAOVaults } = await taskCompletion<
        ApiMakerDAOVault[],
        TaskMeta
      >(taskType);
      commit('makerDAOVaults', convertMakerDAOVaults(makerDAOVaults));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'MakerDAO Vaults',
          description: `${e.message}`
        } as Message,
        { root: true }
      );
    }
  },

  async fetchMakerDAOVaultDetails({
    commit,
    rootState: { session },
    rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
  }) {
    if (!session?.premium || isTaskRunning(TaskType.MAKERDAO_VAULT_DETAILS)) {
      return;
    }

    try {
      const { task_id } = await api.defi.makerDAOVaultDetails();
      const task = createTask(task_id, TaskType.MAKERDAO_VAULT_DETAILS, {
        description: `Fetching MakerDAO Vault Details`,
        ignoreResult: false
      });

      commit('tasks/add', task, { root: true });

      const { result: makerDAOVaultDetails } = await taskCompletion<
        ApiMakerDAOVaultDetails[],
        TaskMeta
      >(TaskType.MAKERDAO_VAULT_DETAILS);

      commit('makerDAOVaultDetails', convertVaultDetails(makerDAOVaultDetails));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'MakerDAO Vault details',
          description: `${e.message}`
        } as Message,
        { root: true }
      );
    }
  },

  async fetchAaveBalances({
    commit,
    rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
  }) {
    const taskType = TaskType.AAVE_BALANCES;
    if (isTaskRunning(taskType)) {
      return;
    }
    try {
      const { task_id } = await api.defi.fetchAaveBalances();
      const task = createTask(task_id, taskType, {
        description: `Fetching Aave balances`,
        ignoreResult: false
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<ApiAaveBalances, TaskMeta>(
        taskType
      );

      commit('aaveBalances', convertAaveBalances(result));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Fetching Aave Balances',
          description: `${e.message}`
        } as Message,
        { root: true }
      );
    }
  },

  async fetchAaveHistory(
    {
      commit,
      rootState: { session },
      rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
    },
    reset?: boolean
  ) {
    const taskType = TaskType.AAVE_HISTORY;
    if (!session?.premium || isTaskRunning(taskType)) {
      return;
    }

    try {
      const { task_id } = await api.defi.fetchAaveHistory(reset);
      const task = createTask(task_id, taskType, {
        description: `Fetching Aave history`,
        ignoreResult: false
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<ApiAaveHistory, TaskMeta>(
        taskType
      );

      commit('aaveHistory', convertAaveHistory(result));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Fetching Aave History',
          description: `${e.message}`
        } as Message,
        { root: true }
      );
    }
  },

  async fetchDefiBalances({
    commit,
    rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
  }) {
    const taskType = TaskType.DEFI_BALANCES;

    if (isTaskRunning(taskType)) {
      return;
    }

    try {
      const { task_id } = await api.defi.fetchAllDefi();
      const task = createTask(task_id, taskType, {
        description: `Fetching Defi Balances`,
        ignoreResult: false
      });

      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<ApiAllDefiProtocols, TaskMeta>(
        taskType
      );

      commit('allDefiProtocols', convertAllDefiProtocols(result));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Fetching Defi Balances',
          description: `${e.message}`
        } as Message,
        { root: true }
      );
    }
  },

  async fetchAllDefi(
    { commit, dispatch, state, rootState: { session } },
    refreshing: boolean = false
  ) {
    if (
      state.status === Status.LOADING ||
      (state.status === Status.LOADED && !refreshing)
    ) {
      return;
    }

    const { activeModules } = session!.generalSettings;

    commit('status', refreshing ? Status.REFRESHING : Status.LOADING);
    commit('defiStatus', refreshing ? Status.REFRESHING : Status.LOADING);
    await dispatch('fetchDefiBalances');
    commit('defiStatus', Status.LOADED);

    if (activeModules.includes('aave')) {
      await dispatch('fetchAaveBalances');
    }

    if (activeModules.includes('makerdao_dsr')) {
      await dispatch('fetchDSRBalances');
    }

    if (activeModules.includes('makerdao_vaults')) {
      await dispatch('fetchMakerDAOVaults');
    }

    commit('status', Status.LOADED);
  },

  async fetchLending(
    { commit, dispatch, state, rootState: { session } },
    refreshing: boolean = false
  ) {
    if (
      state.status === Status.LOADING ||
      (state.status === Status.LOADED && !refreshing)
    ) {
      return;
    }
    const { activeModules } = session!.generalSettings;

    commit('status', refreshing ? Status.REFRESHING : Status.LOADING);

    if (activeModules.includes('makerdao_dsr')) {
      await dispatch('fetchDSRBalances');
    }

    if (activeModules.includes('aave')) {
      await dispatch('fetchAaveBalances');
    }

    commit('status', Status.LOADED);
  },

  async fetchLendingHistory(
    { commit, dispatch, state, rootState: { session } },
    payload?: { refresh?: boolean; reset?: boolean }
  ) {
    if (
      !session?.premium ||
      state.lendingHistoryStatus === Status.LOADING ||
      (state.lendingHistoryStatus === Status.LOADED && !payload?.refresh)
    ) {
      return;
    }

    const { activeModules } = session!.generalSettings;

    commit(
      'lendingHistoryStatus',
      payload?.refresh ? Status.REFRESHING : Status.LOADING
    );

    if (activeModules.includes('makerdao_dsr')) {
      await dispatch('fetchDSRHistory');
    }

    if (activeModules.includes('aave')) {
      await dispatch('fetchAaveHistory', payload?.reset);
    }

    commit('lendingHistoryStatus', Status.LOADED);
  },

  async fetchBorrowing(
    { commit, dispatch, state, rootState: { session } },
    refreshing: boolean = false
  ) {
    if (
      state.status === Status.LOADING ||
      (state.status === Status.LOADED && !refreshing)
    ) {
      return;
    }

    const { activeModules } = session!.generalSettings;

    commit('status', refreshing ? Status.REFRESHING : Status.LOADING);

    if (activeModules.includes('makerdao_vaults')) {
      await dispatch('fetchMakerDAOVaults');
    }

    commit('status', Status.LOADED);
  },

  async fetchBorrowingHistory(
    { commit, dispatch, state, rootState: { session } },
    refreshing: boolean = false
  ) {
    if (
      !session?.premium ||
      state.borrowingHistoryStatus === Status.LOADING ||
      (state.borrowingHistoryStatus === Status.LOADED && !refreshing)
    ) {
      return;
    }

    const { activeModules } = session!.generalSettings;

    commit(
      'borrowingHistoryStatus',
      refreshing ? Status.REFRESHING : Status.LOADING
    );

    if (activeModules.includes('makerdao_vaults')) {
      await dispatch('fetchMakerDAOVaultDetails');
    }

    commit('borrowingHistoryStatus', Status.LOADED);
  }
};
