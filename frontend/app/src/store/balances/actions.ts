import { ActionTree } from 'vuex';
import { currencies } from '@/data/currencies';
import { FiatBalance } from '@/model/blockchain-balances';
import {
  BlockchainMetadata,
  createTask,
  ExchangeMeta,
  taskCompletion,
  TaskMeta
} from '@/model/task';
import { TaskType } from '@/model/task-type';
import {
  convertMakerDAOVaults,
  convertManualBalances,
  convertSupportedAssets,
  convertVaultDetails
} from '@/services/converters';
import { api } from '@/services/rotkehlchen-api';
import {
  ApiMakerDAOVault,
  ApiMakerDAOVaultDetails,
  ApiManualBalance
} from '@/services/types-api';
import { BalanceState } from '@/store/balances/state';
import { notify } from '@/store/notifications/utils';
import { Message, RotkehlchenState } from '@/store/store';
import { Blockchain, Severity, UsdToFiatExchangeRates } from '@/typing/types';
import { bigNumberify } from '@/utils/bignumbers';
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
        description: `Query All Balances`,
        ignoreResult: true
      });

      commit('tasks/add', task, { root: true });
    } catch (e) {
      notify(
        `Failed to fetch all balances: ${e}`,
        'Querying all Balances',
        Severity.ERROR
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
          description: `Query ${name} Balances`,
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
          Severity.ERROR
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
      notify(`Failed fetching exchange rates: ${e.message}`, 'Exchange Rates');
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
        description: `Query ${blockchain || 'Blockchain'} Balances`,
        ignoreResult: false
      } as BlockchainMetadata);
      commit('tasks/add', task, { root: true });
    } catch (e) {
      notify(
        `Error at querying blockchain balances: ${e}`,
        'Querying blockchain balances'
      );
    }
  },
  async fetchFiatBalances({ commit }): Promise<void> {
    try {
      const result = await api.queryFiatBalances();
      const fiatBalances: FiatBalance[] = Object.keys(result).map(currency => ({
        currency: currency,
        amount: bigNumberify(result[currency].amount as string),
        usdValue: bigNumberify(result[currency].usd_value as string)
      }));

      commit('fiatBalances', fiatBalances);
    } catch (e) {
      notify(`Error at querying fiat balances: ${e}`, 'Querying Fiat balances');
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
      await dispatch('fetchFiatBalances');
    }
  },

  async removeAccount({ commit }, payload: BlockchainAccountPayload) {
    const { address, blockchain } = payload;
    const { task_id } = await api.removeBlockchainAccount(blockchain, address);

    const task = createTask(task_id, TaskType.ADD_ACCOUNT, {
      description: `Remove ${blockchain} account ${address}`,
      blockchain
    } as BlockchainMetadata);

    commit('tasks/add', task, { root: true });
  },

  async addAccount({ commit }, payload: BlockchainAccountPayload) {
    const { address, blockchain } = payload;
    const { task_id } = await api.addBlockchainAccount(payload);
    const task = createTask(task_id, TaskType.ADD_ACCOUNT, {
      description: `Adding ${blockchain} account ${address}`,
      blockchain
    } as BlockchainMetadata);

    commit('tasks/add', task, { root: true });
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
      notify(`Failed to accounts: ${e}`, 'Querying accounts', Severity.ERROR);
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
  async fetchDSRBalances({ commit }) {
    const { task_id } = await api.dsrBalance();
    const task = createTask(task_id, TaskType.DSR_BALANCE, {
      description: `Fetching DSR Balances`,
      ignoreResult: false
    });
    commit('tasks/add', task, { root: true });
  },
  async fetchDSRHistory({ commit }) {
    const { task_id } = await api.dsrHistory();
    const task = createTask(task_id, TaskType.DSR_HISTORY, {
      description: `Fetching DSR History`,
      ignoreResult: false
    });
    commit('tasks/add', task, { root: true });
  },
  async fetchSupportedAssets({ commit, state }) {
    if (state.supportedAssets.length > 0) {
      return;
    }
    try {
      const supportedAssets = await api.supportedAssets();
      commit('supportedAssets', convertSupportedAssets(supportedAssets));
    } catch (e) {
      notify(`Error: ${e}`, 'Fetching supported assets', Severity.ERROR);
    }
  },

  async fetchManualBalances({ commit }) {
    try {
      const manualBalances = await api.manualBalances();
      commit('manualBalances', convertManualBalances(manualBalances));
    } catch (e) {
      notify(`Failed: ${e}`, 'Retrieving manual balances', Severity.ERROR);
    }
  },

  async addManualBalance({ commit }, balance: ApiManualBalance) {
    let result = false;
    try {
      const manualBalances = await api.addManualBalances([balance]);
      commit('manualBalances', convertManualBalances(manualBalances));
      result = true;
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Adding Manual Balance',
          description: `${e.message}`
        } as Message,
        { root: true }
      );
    }
    return result;
  },

  async editManualBalance({ commit }, balance: ApiManualBalance) {
    let result = false;
    try {
      const manualBalances = await api.editManualBalances([balance]);
      commit('manualBalances', convertManualBalances(manualBalances));
      result = true;
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Adding Manual Balance',
          description: `${e.message}`
        } as Message,
        { root: true }
      );
    }
    return result;
  },

  async deleteManualBalance({ commit }, label: string) {
    try {
      const manualBalances = await api.deleteManualBalances([label]);
      commit('manualBalances', convertManualBalances(manualBalances));
    } catch (e) {
      commit(
        'setMessage',
        {
          title: 'Deleting Manual Balance',
          description: `${e.message}`
        } as Message,
        { root: true }
      );
    }
  },

  async fetchMakerDAOVaults({
    commit,
    rootGetters: { 'tasks/isTaskRunning': isTaskRunning }
  }) {
    if (isTaskRunning(TaskType.MAKEDAO_VAULTS)) {
      return;
    }

    try {
      const { task_id } = await api.makerDAOVaults();
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
      const { task_id } = await api.makerDAOVaultDetails();
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
