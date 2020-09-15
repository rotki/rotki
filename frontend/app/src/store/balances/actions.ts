import { ActionTree } from 'vuex';
import { currencies } from '@/data/currencies';
import i18n from '@/i18n';
import {
  BlockchainMetadata,
  createTask,
  ExchangeMeta,
  taskCompletion,
  TaskMeta
} from '@/model/task';
import { TaskType } from '@/model/task-type';
import { ManualBalance, ManualBalances } from '@/services/balances/types';
import { balanceKeys } from '@/services/consts';
import { convertSupportedAssets } from '@/services/converters';
import { api } from '@/services/rotkehlchen-api';
import { BalanceState } from '@/store/balances/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { RotkehlchenState } from '@/store/types';
import { showError } from '@/store/utils';
import { Blockchain, UsdToFiatExchangeRates } from '@/typing/types';
import { toMap } from '@/utils/conversion';

export const actions: ActionTree<BalanceState, RotkehlchenState> = {
  async fetchBalances(
    { commit, rootGetters, dispatch },
    payload: AllBalancePayload = {
      ignoreCache: false,
      saveData: false
    }
  ) {
    const { ignoreCache, saveData } = payload;
    const isTaskRunning = rootGetters['tasks/isTaskRunning'];
    if (isTaskRunning(TaskType.QUERY_BALANCES)) {
      return;
    }
    try {
      const result = await api.queryBalancesAsync(ignoreCache, saveData);
      const task = createTask(result.task_id, TaskType.QUERY_BALANCES, {
        title: `Query All Balances`,
        ignoreResult: true
      });

      commit('tasks/add', task, { root: true });
    } catch (e) {
      notify(
        `Failed to fetch all balances: ${e}`,
        'Querying all Balances',
        Severity.ERROR,
        true
      );
    }
    await dispatch('accounts');
  },
  fetchExchangeBalances(
    { commit, rootGetters },
    payload: ExchangeBalancePayload
  ): void {
    const { name, ignoreCache } = payload;
    const isTaskRunning = rootGetters['tasks/isTaskRunning'];
    const taskMetadata = rootGetters['tasks/metadata'];
    const meta: ExchangeMeta = taskMetadata(TaskType.QUERY_EXCHANGE_BALANCES);
    if (isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES) && meta.name === name) {
      return;
    }
    api
      .queryExchangeBalancesAsync(name, ignoreCache)
      .then(result => {
        const meta: ExchangeMeta = {
          name,
          title: `Query ${name} Balances`,
          ignoreResult: false
        };

        const task = createTask(
          result.task_id,
          TaskType.QUERY_EXCHANGE_BALANCES,
          meta
        );

        commit('tasks/add', task, { root: true });
      })
      .catch(reason => {
        notify(
          `Error at querying exchange ${name} balances: ${reason}`,
          'Exchange balance query',
          Severity.ERROR,
          true
        );
      });
  },
  async fetchExchangeRates({ commit }): Promise<void> {
    try {
      const rates = await api.getFiatExchangeRates(
        currencies.map(value => value.ticker_symbol)
      );
      const exchangeRates: UsdToFiatExchangeRates = {};

      for (const asset in rates) {
        if (!Object.prototype.hasOwnProperty.call(rates, asset)) {
          continue;
        }

        exchangeRates[asset] = parseFloat(rates[asset]);
      }
      commit('usdToFiatExchangeRates', exchangeRates);
    } catch (e) {
      notify(
        `Failed fetching exchange rates: ${e.message}`,
        'Exchange Rates',
        Severity.ERROR,
        true
      );
    }
  },
  async fetchBlockchainBalances(
    { commit, rootGetters },
    payload: BlockchainBalancePayload = {
      ignoreCache: false
    }
  ): Promise<void> {
    const { blockchain, ignoreCache } = payload;
    try {
      const taskType = TaskType.QUERY_BLOCKCHAIN_BALANCES;
      const isTaskRunning = rootGetters['tasks/isTaskRunning'];
      const taskMetadata = rootGetters['tasks/metadata'];

      const metadata: BlockchainMetadata = taskMetadata(taskType);
      if (isTaskRunning(taskType) && metadata.blockchain === blockchain) {
        return;
      }
      const result = await api.queryBlockchainBalancesAsync(
        ignoreCache,
        blockchain
      );
      const task = createTask(result.task_id, taskType, {
        blockchain,
        title: `Query ${blockchain || 'Blockchain'} Balances`,
        ignoreResult: false
      } as BlockchainMetadata);
      commit('tasks/add', task, { root: true });
    } catch (e) {
      notify(
        `Error at querying blockchain balances: ${e}`,
        'Querying blockchain balances',
        Severity.ERROR,
        true
      );
    }
  },
  async addExchanges({ commit, dispatch }, exchanges: string[]): Promise<void> {
    commit('connectedExchanges', exchanges);
    for (const exchange of exchanges) {
      await dispatch('fetchExchangeBalances', {
        name: exchange,
        ignoreCache: false
      } as ExchangeBalancePayload);
    }
  },
  async fetch(
    { dispatch },
    payload: { newUser: boolean; exchanges: string[] }
  ): Promise<void> {
    const { exchanges, newUser } = payload;

    await dispatch('fetchExchangeRates');
    await dispatch('fetchBalances');

    if (exchanges) {
      await dispatch('addExchanges', exchanges);
    }

    if (!newUser) {
      await dispatch('fetchBlockchainBalances');
    }
  },

  async removeAccount({ commit, dispatch }, payload: BlockchainAccountPayload) {
    const { address, blockchain } = payload;
    const { task_id } = await api.removeBlockchainAccount(blockchain, address);

    const task = createTask(task_id, TaskType.ADD_ACCOUNT, {
      title: `Remove ${blockchain} account ${address}`,
      blockchain
    } as BlockchainMetadata);

    commit('tasks/add', task, { root: true });
    commit('defi/reset', undefined, { root: true });
    await dispatch('resetDefiStatus', {}, { root: true });
  },

  async addAccount({ commit, dispatch }, payload: BlockchainAccountPayload) {
    const { address, blockchain } = payload;
    const { task_id } = await api.addBlockchainAccount(payload);
    const task = createTask(task_id, TaskType.ADD_ACCOUNT, {
      title: `Adding ${blockchain} account ${address}`,
      blockchain
    } as BlockchainMetadata);

    commit('tasks/add', task, { root: true });
    commit('defi/reset', undefined, { root: true });
    await dispatch('resetDefiStatus', {}, { root: true });
  },

  async editAccount({ commit }, payload: BlockchainAccountPayload) {
    const { blockchain } = payload;
    const accountData = await api.editBlockchainAccount(payload);
    const accountMap = toMap(accountData, 'address');
    commit(blockchain === 'ETH' ? 'ethAccounts' : 'btcAccounts', accountMap);
  },

  async accounts({ commit }) {
    try {
      const [ethAccounts, btcAccounts] = await Promise.all([
        api.accounts('ETH'),
        api.accounts('BTC')
      ]);

      const ethMap = toMap(ethAccounts, 'address');
      const btcMap = toMap(btcAccounts, 'address');
      commit('ethAccounts', ethMap);
      commit('btcAccounts', btcMap);
    } catch (e) {
      notify(
        `Failed to accounts: ${e}`,
        'Querying accounts',
        Severity.ERROR,
        true
      );
    }
  },
  /* Remove a tag from all accounts of the state */
  async removeTag({ commit, state }, tagName: string) {
    const updateEth = { ...state.ethAccounts };
    for (const key in updateEth) {
      const tags = updateEth[key].tags;
      const index = tags.indexOf(tagName);
      updateEth[key] = {
        ...updateEth[key],
        tags:
          index === -1
            ? tags
            : [...tags.slice(0, index), ...tags.slice(index + 1)]
      };
    }
    const updateBtc = { ...state.btcAccounts };
    for (const key in updateBtc) {
      const tags = updateBtc[key].tags;
      const index = tags.indexOf(tagName);
      updateBtc[key] = {
        ...updateBtc[key],
        tags:
          index === -1
            ? tags
            : [...tags.slice(0, index), ...tags.slice(index + 1)]
      };
    }
    commit('ethAccounts', updateEth);
    commit('btcAccounts', updateBtc);
  },

  async fetchSupportedAssets({ commit, state }) {
    if (state.supportedAssets.length > 0) {
      return;
    }
    try {
      const supportedAssets = await api.supportedAssets();
      commit('supportedAssets', convertSupportedAssets(supportedAssets));
    } catch (e) {
      notify(`Error: ${e}`, 'Fetching supported assets', Severity.ERROR, true);
    }
  },

  async fetchManualBalances({ commit }) {
    try {
      const taskType = TaskType.MANUAL_BALANCES;
      const { taskId } = await api.balances.manualBalances();
      const task = createTask<TaskMeta>(taskId, taskType, {
        title: i18n.tc('actions.manual_balances.task.title'),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<ManualBalances, TaskMeta>(
        taskType
      );

      commit('manualBalances', result.balances);
    } catch (e) {
      notify(
        `Failed: ${e}`,
        'Retrieving manual balances',
        Severity.ERROR,
        true
      );
    }
  },

  async addManualBalance({ commit }, balance: ManualBalance) {
    let result = false;
    try {
      const { balances } = await api.balances.addManualBalances([balance]);
      commit('manualBalances', balances);
      result = true;
    } catch (e) {
      showError(`${e.message}`, 'Adding Manual Balance');
    }
    return result;
  },

  async editManualBalance({ commit }, balance: ManualBalance) {
    let result = false;
    try {
      const { balances } = await api.balances.editManualBalances([balance]);
      commit('manualBalances', balances);
      result = true;
    } catch (e) {
      showError(`${e.message}`, 'Editing Manual Balance');
    }
    return result;
  },

  async deleteManualBalance({ commit }, label: string) {
    try {
      const { balances } = await api.balances.deleteManualBalances([label]);
      commit('manualBalances', balances);
    } catch (e) {
      showError(`${e.message}`, 'Deleting Manual Balance');
    }
  }
};

export interface BlockchainAccountPayload {
  readonly address: string;
  readonly blockchain: Blockchain;
  readonly label?: string;
  readonly tags: string[];
}

export interface ExchangeBalancePayload {
  readonly name: string;
  readonly ignoreCache: boolean;
}

export interface BlockchainBalancePayload {
  readonly blockchain?: Blockchain;
  readonly ignoreCache: boolean;
}

export interface AllBalancePayload {
  readonly ignoreCache: boolean;
  readonly saveData: boolean;
}
