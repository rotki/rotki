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
import { blockchainBalanceKeys } from '@/services/balances/consts';
import {
  BlockchainBalances,
  ManualBalance,
  ManualBalances
} from '@/services/balances/types';
import { balanceKeys } from '@/services/consts';
import { convertSupportedAssets } from '@/services/converters';
import { api } from '@/services/rotkehlchen-api';
import {
  AllBalancePayload,
  AssetBalances,
  BalanceState,
  BlockchainAccountPayload,
  BlockchainBalancePayload,
  ExchangeBalancePayload,
  ExchangePayload
} from '@/store/balances/types';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import store from '@/store/store';
import { RotkehlchenState } from '@/store/types';
import { showError } from '@/store/utils';
import { BTC, ETH, UsdToFiatExchangeRates } from '@/typing/types';
import { assert } from '@/utils/assertions';
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

  async fetchExchangeBalances(
    { commit, rootGetters },
    payload: ExchangeBalancePayload
  ): Promise<void> {
    const { name, ignoreCache } = payload;
    const isTaskRunning = rootGetters['tasks/isTaskRunning'];
    const taskMetadata = rootGetters['tasks/metadata'];
    const taskType = TaskType.QUERY_EXCHANGE_BALANCES;

    const meta: ExchangeMeta = taskMetadata(taskType);

    if (isTaskRunning(taskType) && meta.name === name) {
      return;
    }

    try {
      const { taskId } = await api.queryExchangeBalances(name, ignoreCache);
      const meta: ExchangeMeta = {
        name,
        title: i18n.tc('actions.balances.exchange_balances.task.title', 0, {
          name
        }),
        ignoreResult: false,
        numericKeys: balanceKeys
      };

      const task = createTask(taskId, taskType, meta);

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<AssetBalances, ExchangeMeta>(
        taskType,
        `${taskId}`
      );

      commit('addExchangeBalances', {
        name: meta.name,
        balances: result
      });
    } catch (e) {
      const message = i18n.tc(
        'actions.balances.exchange_balances.error.message',
        0,
        { name, error: e.message }
      );
      const title = i18n.tc(
        'actions.balances.exchange_balances.error.title',
        0,
        {
          name
        }
      );
      notify(message, title, Severity.ERROR, true);
    }
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
      const { taskId } = await api.balances.queryBlockchainBalances(
        ignoreCache,
        blockchain
      );
      const task = createTask(taskId, taskType, {
        blockchain,
        title: `Query ${blockchain || 'Blockchain'} Balances`,
        ignoreResult: false,
        numericKeys: blockchainBalanceKeys
      } as BlockchainMetadata);
      commit('tasks/add', task, { root: true });

      const {
        result: { perAccount, totals }
      } = await taskCompletion<BlockchainBalances, BlockchainMetadata>(
        taskType
      );
      const { ETH, BTC } = perAccount;

      store.commit('balances/updateEth', ETH);
      store.commit('balances/updateBtc', BTC);
      store.commit('balances/updateTotals', totals);
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
    const { taskId } = await api.removeBlockchainAccount(blockchain, address);

    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      const task = createTask(taskId, taskType, {
        title: i18n.tc(
          'actions.balances.blockchain_account_removal.task.title',
          0,
          {
            blockchain
          }
        ),
        description: i18n.tc(
          'actions.balances.blockchain_account_removal.task.description',
          0,
          { address }
        ),
        blockchain,
        numericKeys: blockchainBalanceKeys
      } as BlockchainMetadata);

      commit('tasks/add', task, { root: true });
      const {
        result: { perAccount, totals }
      } = await taskCompletion<BlockchainBalances, BlockchainMetadata>(
        taskType
      );
      const { ETH: ethBalances, BTC: btcBalances } = perAccount;

      if (blockchain === ETH) {
        store.commit('balances/updateEth', ethBalances);
      } else {
        store.commit('balances/updateBtc', btcBalances);
      }
      store.commit('balances/updateTotals', totals);

      store.dispatch('balances/accounts').then();
      commit('defi/reset', undefined, { root: true });
      await dispatch('resetDefiStatus', {}, { root: true });
    } catch (e) {
      const title = i18n.tc(
        'actions.balances.blockchain_account_removal.error.title',
        0,
        { address, blockchain }
      );
      const description = i18n.tc(
        'actions.balances.blockchain_account_removal.error.description',
        0,
        {
          error: e.message
        }
      );
      notify(description, title, Severity.ERROR, true);
    }
  },

  async addAccount({ commit, dispatch }, payload: BlockchainAccountPayload) {
    const { address, blockchain } = payload;
    try {
      const taskType = TaskType.ADD_ACCOUNT;
      const { taskId } = await api.addBlockchainAccount(payload);

      const task = createTask(taskId, taskType, {
        title: i18n.tc(
          'actions.balances.blockchain_account_add.task.title',
          0,
          { blockchain }
        ),
        description: i18n.tc(
          'actions.balances.blockchain_account_add.task.description',
          0,
          { address }
        ),
        blockchain,
        numericKeys: blockchainBalanceKeys
      } as BlockchainMetadata);

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<
        BlockchainBalances,
        BlockchainMetadata
      >(taskType);

      const { perAccount, totals } = result;
      const { ETH: ethBalances, BTC: btcBalances } = perAccount;

      if (blockchain === ETH) {
        store.commit('balances/updateEth', ethBalances);
      } else {
        store.commit('balances/updateBtc', btcBalances);
      }
      store.commit('balances/updateTotals', totals);

      store.dispatch('balances/accounts').then();
      commit('defi/reset', undefined, { root: true });
      await dispatch('resetDefiStatus', {}, { root: true });
    } catch (e) {
      const title = i18n.tc(
        'actions.balances.blockchain_account_add.error.title',
        0,
        { address, blockchain }
      );
      const description = i18n.tc(
        'actions.balances.blockchain_account_add.error.description',
        0,
        {
          error: e.message
        }
      );
      notify(description, title, Severity.ERROR, true);
    }
  },

  async editAccount({ commit }, payload: BlockchainAccountPayload) {
    const { blockchain } = payload;
    const accountData = await api.editBlockchainAccount(payload);
    const accountMap = toMap(accountData, 'address');
    commit(blockchain === ETH ? 'ethAccounts' : 'btcAccounts', accountMap);
  },

  async accounts({ commit }) {
    try {
      const [ethAccounts, btcAccounts] = await Promise.all([
        api.accounts(ETH),
        api.accounts(BTC)
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
  },

  async setupExchange(
    { commit, dispatch },
    { apiKey, apiSecret, exchange, passphrase }: ExchangePayload
  ): Promise<boolean> {
    try {
      const success = await api.setupExchange(
        exchange,
        apiKey,
        apiSecret,
        passphrase ?? null
      );
      commit('addExchange', exchange);
      dispatch('fetchExchangeBalances', {
        name: exchange
      }).then();
      return success;
    } catch (e) {
      showError(
        i18n.tc('actions.balances.exchange_setup.description', 0, {
          exchange,
          error: e.message
        }),
        i18n.tc('actions.balances.exchange_setup.title')
      );
      return false;
    }
  },

  async removeExchange(
    { commit, state: { connectedExchanges } },
    exchange: string
  ): Promise<boolean> {
    try {
      const success = await api.removeExchange(exchange);
      if (success) {
        const exchangeIndex = connectedExchanges.findIndex(
          value => value === exchange
        );
        assert(
          exchangeIndex >= 0,
          `${exchange} not found in ${connectedExchanges.join(', ')}`
        );
        commit('removeExchange', exchange);
      }
      return success;
    } catch (e) {
      showError(
        i18n.tc('actions.balances.exchange_removal.description', 0, {
          exchange,
          error: e.message
        }),
        i18n.tc('actions.balances.exchange_removal.title')
      );
      return false;
    }
  }
};
