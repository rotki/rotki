import { ActionTree } from 'vuex';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import {
  ApiAaveBalances,
  ApiAaveHistory,
  ApiMakerDAOVault,
  ApiMakerDAOVaultDetails
} from '@/services/defi/types';
import { api } from '@/services/rotkehlchen-api';
import {
  convertAaveBalances,
  convertAaveHistory,
  convertMakerDAOVaults,
  convertVaultDetails
} from '@/store/defi/converters';
import { DefiState } from '@/store/defi/state';
import { Message, RotkehlchenState } from '@/store/store';

export const actions: ActionTree<DefiState, RotkehlchenState> = {
  async fetchDSRBalances({ commit }) {
    const { task_id } = await api.defi.dsrBalance();
    const task = createTask(task_id, TaskType.DSR_BALANCE, {
      description: `Fetching DSR Balances`,
      ignoreResult: false
    });
    commit('tasks/add', task, { root: true });
  },

  async fetchDSRHistory({ commit }) {
    const { task_id } = await api.defi.dsrHistory();
    const task = createTask(task_id, TaskType.DSR_HISTORY, {
      description: `Fetching DSR History`,
      ignoreResult: false
    });
    commit('tasks/add', task, { root: true });
  },

  async fetchMakerDAOVaults({
    commit,
    rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
  }) {
    if (isTaskRunning(TaskType.MAKEDAO_VAULTS)) {
      return;
    }

    try {
      const { task_id } = await api.defi.makerDAOVaults();
      const task = createTask(task_id, TaskType.MAKEDAO_VAULTS, {
        description: `Fetching MakerDAO Vaults`,
        ignoreResult: false
      });

      commit('tasks/add', task, { root: true });

      const { result: makerDAOVaults } = await taskCompletion<
        ApiMakerDAOVault[],
        TaskMeta
      >(TaskType.MAKEDAO_VAULTS);
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

  async fetchAaveHistory({
    commit,
    rootState: { session },
    rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
  }) {
    const taskType = TaskType.AAVE_HISTORY;
    if (!session?.premium || isTaskRunning(taskType)) {
      return;
    }

    try {
      const { task_id } = await api.defi.fetchAaveHistory();
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
  }
};
