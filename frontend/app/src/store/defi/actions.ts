import { ActionTree } from 'vuex';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
import {
  ApiMakerDAOVault,
  ApiMakerDAOVaultDetails,
  Watcher,
  WatcherTypes
} from '@/services/defi/types';
import { api } from '@/services/rotkehlchen-api';
import {
  convertMakerDAOVaults,
  convertVaultDetails
} from '@/store/defi/converters';
import { DefiState } from '@/store/defi/state';
import { notify } from '@/store/notifications/utils';
import { Message, RotkehlchenState } from '@/store/store';
import { Severity } from '@/typing/types';

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

  async fetchWatchers({ commit, rootState: { session } }) {
    if (!session?.premium) {
      return;
    }

    try {
      const watchers = await api.defi.watchers();
      commit('watchers', watchers);
    } catch (e) {
      notify(`Error: ${e}`, 'Fetching watchers', Severity.ERROR);
    }
  },

  async addWatchers(
    { commit },
    watchers: Omit<Watcher<WatcherTypes>, 'identifier'>[]
  ) {
    const updatedWatchers = await api.defi.addWatcher(watchers);
    commit('watchers', updatedWatchers);
    return updatedWatchers;
  },

  async deleteWatchers({ commit }, identifiers: string[]) {
    const updatedWatchers = await api.defi.deleteWatcher(identifiers);
    commit('watchers', updatedWatchers);
    return updatedWatchers;
  },

  async editWatchers({ commit }, watchers: Watcher<WatcherTypes>[]) {
    const updatedWatchers = await api.defi.editWatcher(watchers);
    commit('watchers', updatedWatchers);
    return updatedWatchers;
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
  }
};
