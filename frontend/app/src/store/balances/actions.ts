import { ActionTree } from 'vuex';
import { currencies, CURRENCY_USD } from '@/data/currencies';
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
  Balances,
  BlockchainBalances,
  BtcBalances,
  ManualBalance,
  ManualBalances,
  ManualBalanceWithValue
} from '@/services/balances/types';
import { balanceKeys } from '@/services/consts';
import { convertSupportedAssets } from '@/services/converters';
import { api } from '@/services/rotkehlchen-api';
import { XpubAccountData } from '@/services/types-api';
import { chainSection } from '@/store/balances/const';
import { MUTATION_UPDATE_PRICES } from '@/store/balances/mutation-types';
import {
  AccountPayload,
  AddAccountsPayload,
  AllBalancePayload,
  AssetBalances,
  AssetPriceResponse,
  AssetPrices,
  BalanceState,
  BlockchainAccountPayload,
  BlockchainBalancePayload,
  ExchangeBalancePayload,
  ExchangePayload,
  OracleCachePayload,
  XpubPayload
} from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { ActionStatus, RotkehlchenState, StatusPayload } from '@/store/types';
import { isLoading, setStatus, showError } from '@/store/utils';
import { Writeable } from '@/types';
import {
  Blockchain,
  BTC,
  ETH,
  ExchangeRates,
  KSM,
  SupportedBlockchains
} from '@/typing/types';
import { chunkArray } from '@/utils/array';
import { assert } from '@/utils/assertions';

function removeTag(tags: string[] | null, tagName: string): string[] | null {
  if (!tags) {
    return null;
  }

  const index = tags.indexOf(tagName);

  if (index < 0) {
    return null;
  }

  return [...tags.slice(0, index), ...tags.slice(index + 1)];
}

function removeTags<T extends { tags: string[] | null }>(
  data: T[],
  tagName: string
): T[] {
  const accounts = [...data];
  for (let i = 0; i < accounts.length; i++) {
    const account = accounts[i];
    const tags = removeTag(account.tags, tagName);

    if (!tags) {
      continue;
    }

    accounts[i] = {
      ...accounts[i],
      tags
    };
  }
  return accounts;
}

const updateBalancePrice: (
  balances: Balances,
  prices: AssetPrices
) => Balances = (balances, assetPrices) => {
  for (const asset in balances) {
    const assetPrice = assetPrices[asset];
    if (!assetPrice) {
      continue;
    }
    const assetInfo = balances[asset];
    balances[asset] = {
      amount: assetInfo.amount,
      usdValue: assetInfo.amount.times(assetPrice)
    };
  }
  return balances;
};

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
        title: i18n.t('actions.balances.all_balances.task.title').toString(),
        ignoreResult: true
      });

      commit('tasks/add', task, { root: true });
    } catch (e) {
      notify(
        i18n
          .t('actions.balances.all_balances.error.message', {
            message: e.message
          })
          .toString(),
        i18n.t('actions.balances.all_balances.error.title').toString(),
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
      const exchangeRates: ExchangeRates = {};

      for (const asset in rates) {
        if (!Object.prototype.hasOwnProperty.call(rates, asset)) {
          continue;
        }

        exchangeRates[asset] = parseFloat(rates[asset]);
      }
      commit('usdToFiatExchangeRates', exchangeRates);
    } catch (e) {
      notify(
        i18n
          .t('actions.balances.exchange_rates.error.message', {
            message: e.message
          })
          .toString(),
        i18n.t('actions.balances.exchange_rates.error.title').toString(),
        Severity.ERROR,
        true
      );
    }
  },
  async fetchBlockchainBalances(
    { commit, rootGetters: { status }, dispatch },
    payload: BlockchainBalancePayload = {
      ignoreCache: false
    }
  ): Promise<void> {
    const { blockchain, ignoreCache } = payload;

    const chains: Blockchain[] = [];
    if (!blockchain) {
      chains.push(...SupportedBlockchains);
    } else {
      chains.push(blockchain);
    }

    const fetch: (chain: Blockchain) => Promise<void> = async (
      chain: Blockchain
    ) => {
      const section = chainSection[chain];
      const currentStatus = status(section);

      if (isLoading(currentStatus)) {
        return;
      }

      const newStatus =
        currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
      setStatus(newStatus, section, status, commit);

      const { taskId } = await api.balances.queryBlockchainBalances(
        ignoreCache,
        chain
      );
      const taskType = TaskType.QUERY_BLOCKCHAIN_BALANCES;
      const task = createTask(taskId, taskType, {
        chain,
        title: `Query ${chain} Balances`,
        ignoreResult: false,
        numericKeys: blockchainBalanceKeys
      } as BlockchainMetadata);
      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<
        BlockchainBalances,
        BlockchainMetadata
      >(taskType, taskId.toString());
      await dispatch('updateBalances', {
        chain: chain,
        balances: result
      });
      setStatus(Status.LOADED, section, status, commit);
    };
    try {
      await Promise.all(chains.map(fetch));
    } catch (e) {
      const message = i18n.tc(
        'actions.balances.blockchain.error.description',
        0,
        {
          error: e.message
        }
      );
      notify(
        message,
        i18n.tc('actions.balances.blockchain.error.title'),
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
    { commit, dispatch },
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
    } else {
      const loaded = Status.LOADED;
      const oldStatus = () => Status.NONE;
      setStatus(loaded, Section.BLOCKCHAIN_ETH, oldStatus, commit);
      setStatus(loaded, Section.BLOCKCHAIN_BTC, oldStatus, commit);
    }
  },

  async updateBalances(
    { commit, dispatch },
    payload: { chain?: Blockchain; balances: BlockchainBalances }
  ): Promise<void> {
    const { perAccount, totals } = payload.balances;
    const { ETH: ethBalances, BTC: btcBalances, KSM: ksmBalances } = perAccount;
    const chain = payload.chain;

    if (!chain || chain === ETH) {
      commit('updateEth', ethBalances ?? {});
    }

    if (!chain || chain === KSM) {
      commit('updateKsm', ksmBalances ?? {});
    }

    if (!chain || chain === BTC) {
      commit('updateBtc', btcBalances ?? {});
    }

    commit('updateTotals', totals.assets);
    commit('updateLiabilities', totals.liabilities);
    dispatch('accounts').then();
  },

  async deleteXpub({ commit, dispatch, rootGetters }, payload: XpubPayload) {
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      const isTaskRunning = rootGetters['tasks/isTaskRunning'];
      if (isTaskRunning(taskType)) {
        return;
      }
      const { taskId } = await api.deleteXpub(payload);
      const task = createTask(taskId, taskType, {
        title: i18n.tc('actions.balances.xpub_removal.task.title'),
        description: i18n.tc(
          'actions.balances.xpub_removal.task.description',
          0,
          {
            xpub: payload.xpub
          }
        ),
        blockchain: BTC,
        numericKeys: blockchainBalanceKeys
      } as BlockchainMetadata);
      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<
        BlockchainBalances,
        BlockchainMetadata
      >(taskType);
      await dispatch('updateBalances', { chain: BTC, balances: result });
    } catch (e) {
      const title = i18n.tc('actions.balances.xpub_removal.error.title');
      const description = i18n.tc(
        'actions.balances.xpub_removal.error.description',
        0,
        {
          xpub: payload.xpub,
          error: e.message
        }
      );
      notify(description, title, Severity.ERROR, true);
    }
  },

  async removeAccount({ commit, dispatch }, payload: BlockchainAccountPayload) {
    const { accounts, blockchain } = payload;
    assert(accounts, 'Accounts was empty');
    const { taskId } = await api.removeBlockchainAccount(blockchain, accounts);

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
          { count: accounts.length }
        ),
        blockchain,
        numericKeys: blockchainBalanceKeys
      } as BlockchainMetadata);

      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<
        BlockchainBalances,
        BlockchainMetadata
      >(taskType);

      await dispatch('updateBalances', { chain: blockchain, balances: result });
      commit('defi/reset', undefined, { root: true });
      await dispatch('resetDefiStatus', {}, { root: true });
    } catch (e) {
      const title = i18n.tc(
        'actions.balances.blockchain_account_removal.error.title',
        0,
        { count: accounts.length, blockchain }
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

  async addAccounts(
    { state, commit, dispatch, rootGetters },
    { blockchain, payload }: AddAccountsPayload
  ): Promise<void> {
    const taskType = TaskType.ADD_ACCOUNT;
    const isTaskRunning = rootGetters['tasks/isTaskRunning'];
    if (isTaskRunning(taskType)) {
      return;
    }
    const existingAddresses = state.ethAccounts.map(address =>
      address.address.toLocaleLowerCase()
    );
    const accounts = payload.filter(
      value => !existingAddresses.includes(value.address.toLocaleLowerCase())
    );

    if (accounts.length === 0) {
      const title = i18n.tc(
        'actions.balances.blockchain_accounts_add.no_new.title',
        0,
        { blockchain }
      );
      const description = i18n.tc(
        'actions.balances.blockchain_accounts_add.no_new.description'
      );
      notify(description, title, Severity.INFO, true);
      return;
    }

    const addAccount = async (
      blockchain: Blockchain,
      { address, label, tags }: AccountPayload
    ) => {
      const { taskId } = await api.addBlockchainAccount({
        blockchain,
        address,
        label,
        tags
      });

      const task = createTask(taskId, taskType, {
        title: i18n.tc(
          'actions.balances.blockchain_accounts_add.task.title',
          0,
          { blockchain }
        ),
        description: i18n.tc(
          'actions.balances.blockchain_accounts_add.task.description',
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
      >(taskType, `${taskId}`);
      await dispatch('updateBalances', { chain: blockchain, balances: result });
    };

    const additions = accounts.map(value =>
      addAccount(blockchain, value).catch(() => {})
    );
    Promise.all(additions)
      .then(async () => {
        const options = { root: true };
        commit('defi/reset', undefined, options);
        await dispatch('resetDefiStatus', {}, options);
        await dispatch('refreshPrices', false);
      })
      .catch(e => {
        const title = i18n.tc(
          'actions.balances.blockchain_accounts_add.error.title',
          0,
          { blockchain }
        );
        const description = i18n.tc(
          'actions.balances.blockchain_accounts_add.error.description',
          0,
          {
            error: e.message,
            address: accounts.length,
            blockchain
          }
        );
        notify(description, title, Severity.ERROR, true);
      });
  },

  async addAccount({ commit, dispatch }, payload: BlockchainAccountPayload) {
    const { address, blockchain } = payload;
    const taskType = TaskType.ADD_ACCOUNT;
    const { taskId } = await api.addBlockchainAccount(payload);

    const task = createTask(taskId, taskType, {
      title: i18n.tc('actions.balances.blockchain_account_add.task.title', 0, {
        blockchain
      }),
      description: i18n.tc(
        'actions.balances.blockchain_account_add.task.description',
        0,
        { address }
      ),
      blockchain,
      numericKeys: blockchainBalanceKeys
    } as BlockchainMetadata);

    commit('tasks/add', task, { root: true });

    taskCompletion<BlockchainBalances, BlockchainMetadata>(taskType)
      .then(async ({ result }) => {
        await dispatch('updateBalances', {
          chain: blockchain,
          balances: result
        });
        await commit('defi/reset', undefined, { root: true });
        await dispatch('resetDefiStatus', {}, { root: true });
        await dispatch('refreshPrices', false);
      })
      .catch(e => {
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
      });
  },

  async editAccount({ commit }, payload: BlockchainAccountPayload) {
    const { blockchain } = payload;
    const isBTC = blockchain === BTC;
    if (!isBTC) {
      const accountData = await api.editAccount(payload);

      if (blockchain === ETH) {
        commit('ethAccounts', accountData);
      } else {
        commit('ksmAccounts', accountData);
      }
    } else {
      const accountData = await api.editBtcAccount(payload);
      commit('btcAccounts', accountData);
    }
  },

  async accounts({ commit }) {
    try {
      const [ethAccounts, btcAccounts, ksmAccounts] = await Promise.all([
        api.accounts(ETH),
        api.btcAccounts(),
        api.accounts(KSM)
      ]);

      commit('ethAccounts', ethAccounts);
      commit('btcAccounts', btcAccounts);
      commit('ksmAccounts', ksmAccounts);
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
    commit('ethAccounts', removeTags(state.ethAccounts, tagName));
    commit('ksmAccounts', removeTags(state.ksmAccounts, tagName));
    const btcAccounts = state.btcAccounts;
    const standalone = removeTags(btcAccounts.standalone, tagName);

    const xpubs: XpubAccountData[] = [];

    for (let i = 0; i < btcAccounts.xpubs.length; i++) {
      const xpub = btcAccounts.xpubs[i];
      xpubs.push({
        ...xpub,
        tags: removeTag(xpub.tags, tagName),
        addresses: xpub.addresses ? removeTags(xpub.addresses, tagName) : null
      });
    }

    commit('btcAccounts', {
      standalone,
      xpubs
    });
  },
  async fetchNetvalueData({ commit, rootState: { session } }) {
    if (!session?.premium) {
      return;
    }
    try {
      const netvalueData = await api.queryNetvalueData();
      commit('netvalueData', netvalueData);
    } catch (e) {
      notify(
        i18n
          .t('actions.balances.net_value.error.message', { message: e.message })
          .toString(),
        i18n.t('actions.balances.net_value.error.title').toString(),
        Severity.ERROR
      );
    }
  },

  async fetchSupportedAssets({ commit, state }) {
    if (state.supportedAssets.length > 0) {
      return;
    }
    try {
      const supportedAssets = await api.supportedAssets();
      commit('supportedAssets', convertSupportedAssets(supportedAssets));
    } catch (e) {
      notify(
        i18n
          .t('actions.balances.supported_assets.error.message', {
            message: e.message
          })
          .toString(),
        i18n.t('actions.balances.supported_assets.error.title').toString(),
        Severity.ERROR,
        true
      );
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
        i18n
          .t('actions.balances.manual_balances.error.message', {
            message: e.message
          })
          .toString(),
        i18n.t('actions.balances.manual_balances.error.title').toString(),
        Severity.ERROR,
        true
      );
    }
  },

  async addManualBalance({ commit, dispatch }, balance: ManualBalance) {
    let result = false;
    try {
      const { balances } = await api.balances.addManualBalances([balance]);
      commit('manualBalances', balances);
      result = true;
      dispatch('refreshPrices', false);
    } catch (e) {
      showError(
        `${e.message}`,
        i18n.t('actions.balances.manual_add.error.title').toString()
      );
    }
    return result;
  },

  async editManualBalance({ commit, dispatch }, balance: ManualBalance) {
    let result = false;
    try {
      const { balances } = await api.balances.editManualBalances([balance]);
      commit('manualBalances', balances);
      result = true;
      dispatch('refreshPrices', false);
    } catch (e) {
      showError(
        `${e.message}`,
        i18n.t('actions.balances.manual_edit.error.title').toString()
      );
    }
    return result;
  },

  async deleteManualBalance({ commit }, label: string) {
    try {
      const { balances } = await api.balances.deleteManualBalances([label]);
      commit('manualBalances', balances);
    } catch (e) {
      showError(
        `${e.message}`,
        i18n.t('actions.balances.manual_delete.error.title').toString()
      );
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
  },

  async updatePrices({ commit, state }, prices: AssetPrices): Promise<void> {
    const manualBalances = [...state.manualBalances];
    const totals = { ...state.totals };
    const eth = { ...state.eth };
    const btc: BtcBalances = {
      standalone: state.btc.standalone ? { ...state.btc.standalone } : {},
      xpubs: state.btc.xpubs ? [...state.btc.xpubs] : []
    };
    const kusama = { ...state.ksm };
    const exchanges = { ...state.exchangeBalances };

    for (const asset in totals) {
      const assetPrice = prices[asset];
      if (!assetPrice) {
        continue;
      }
      totals[asset] = {
        amount: totals[asset].amount,
        usdValue: totals[asset].amount.times(assetPrice)
      };
    }
    commit('updateTotals', totals);

    for (let i = 0; i < manualBalances.length; i++) {
      const balance: Writeable<ManualBalanceWithValue> = manualBalances[i];
      const assetPrice = prices[balance.asset];
      if (!assetPrice) {
        continue;
      }
      balance.usdValue = balance.amount.times(assetPrice);
    }
    commit('manualBalances', manualBalances);

    for (const address in eth) {
      const balances = eth[address];
      eth[address] = {
        assets: updateBalancePrice(balances.assets, prices),
        liabilities: updateBalancePrice(balances.liabilities, prices)
      };
    }

    commit('updateEth', eth);

    const btcPrice = prices[BTC];
    if (btcPrice) {
      for (const address in btc.standalone) {
        const balance = btc.standalone[address];
        btc.standalone[address] = {
          amount: balance.amount,
          usdValue: balance.amount.times(btcPrice)
        };
      }
      for (let i = 0; i < btc.xpubs.length; i++) {
        const xpub = btc.xpubs[i];
        for (const address in xpub.addresses) {
          const balance = xpub.addresses[address];
          xpub.addresses[address] = {
            amount: balance.amount,
            usdValue: balance.amount.times(btcPrice)
          };
        }
      }
    }

    commit('updateBtc', btc);

    for (const address in kusama) {
      const balances = kusama[address];
      kusama[address] = {
        assets: updateBalancePrice(balances.assets, prices),
        liabilities: updateBalancePrice(balances.liabilities, prices)
      };
    }

    commit('updateKsm', kusama);

    for (const exchange in exchanges) {
      exchanges[exchange] = updateBalancePrice(exchanges[exchange], prices);
    }

    commit('updateExchangeBalances', exchanges);
  },

  async fetchPrices(
    {
      state,
      commit,
      rootGetters: {
        'tasks/isTaskRunning': isTaskRunning,
        'balances/aggregatedAssets': assets
      }
    },
    ignoreCache: boolean
  ): Promise<void> {
    const taskType = TaskType.UPDATE_PRICES;
    if (isTaskRunning(taskType)) {
      return;
    }
    const fetchPrices: (assets: string[]) => Promise<void> = async assets => {
      const { taskId } = await api.balances.prices(
        assets,
        CURRENCY_USD,
        ignoreCache
      );
      const task = createTask(taskId, taskType, {
        title: i18n.t('actions.session.fetch_prices.task.title').toString(),
        ignoreResult: false,
        numericKeys: null
      });
      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<AssetPriceResponse, TaskMeta>(
        taskType,
        `${taskId}`
      );
      commit(MUTATION_UPDATE_PRICES, {
        ...state.prices,
        ...result.assets
      });
    };

    try {
      await Promise.all(
        chunkArray<string>(assets, 100).map(value => fetchPrices(value))
      );
    } catch (e) {
      const title = i18n
        .t('actions.session.fetch_prices.error.title')
        .toString();
      const message = i18n
        .t('actions.session.fetch_prices.error.message', {
          error: e.message
        })
        .toString();
      notify(message, title, Severity.ERROR, true);
    }
  },

  async refreshPrices(
    { commit, dispatch, state },
    ignoreCache: boolean
  ): Promise<void> {
    commit(
      'setStatus',
      {
        section: Section.PRICES,
        status: Status.LOADING
      } as StatusPayload,
      { root: true }
    );
    await dispatch('fetchExchangeRates');
    await dispatch('fetchPrices', ignoreCache);
    await dispatch('updatePrices', state.prices);
    commit(
      'setStatus',
      {
        section: Section.PRICES,
        status: Status.LOADED
      } as StatusPayload,
      { root: true }
    );
  },

  async createOracleCache(
    { commit, rootGetters: { 'tasks/isTaskRunning': isTaskRunning } },
    { fromAsset, purgeOld, source, toAsset }: OracleCachePayload
  ): Promise<ActionStatus> {
    const taskType = TaskType.CREATE_PRICE_CACHE;
    if (isTaskRunning(taskType)) {
      return {
        success: false,
        message: i18n
          .t('actions.balances.create_oracle_cache.already_running')
          .toString()
      };
    }
    try {
      const { taskId } = await api.balances.createPriceCache(
        source,
        fromAsset,
        toAsset,
        purgeOld
      );
      const task = createTask(taskId, taskType, {
        title: i18n
          .t('actions.balances.create_oracle_cache.task', {
            fromAsset,
            toAsset,
            source
          })
          .toString(),
        ignoreResult: false,
        numericKeys: null
      });
      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<boolean, TaskMeta>(
        taskType,
        `${taskId}`
      );
      return {
        success: result
      };
    } catch (e) {
      return {
        success: false,
        message: i18n
          .t('actions.balances.create_oracle_cache.failed', {
            fromAsset,
            toAsset,
            source,
            error: e.message
          })
          .toString()
      };
    }
  }
};
