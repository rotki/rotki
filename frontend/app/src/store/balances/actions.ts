import { BigNumber } from 'bignumber.js';
import { ActionTree } from 'vuex';
import { currencies, CURRENCY_USD } from '@/data/currencies';
import i18n from '@/i18n';
import { Exchange } from '@/model/action-result';
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
import { MODULE_LOOPRING } from '@/services/session/consts';
import { SupportedModules } from '@/services/session/types';
import { XpubAccountData } from '@/services/types-api';
import { chainSection } from '@/store/balances/const';
import {
  MUTATION_UPDATE_LOOPRING_BALANCES,
  MUTATION_UPDATE_PRICES
} from '@/store/balances/mutation-types';
import {
  AccountAssetBalances,
  AccountPayload,
  AddAccountsPayload,
  AllBalancePayload,
  AssetBalances,
  AssetPriceResponse,
  AssetPrices,
  BalanceState,
  BlockchainAccountPayload,
  BlockchainBalancePayload,
  ERC20Token,
  ExchangeBalancePayload,
  ExchangeSetupPayload,
  HistoricPricePayload,
  HistoricPrices,
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
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';
import { chunkArray } from '@/utils/data';
import { convertFromTimestamp } from '@/utils/date';

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

  async fetchConnectedExchangeBalances({
    dispatch,
    state: { connectedExchanges: exchanges }
  }): Promise<void> {
    for (const exchange of exchanges) {
      await dispatch('fetchExchangeBalances', {
        location: exchange.location,
        ignoreCache: false
      } as ExchangeBalancePayload);
    }
  },

  async fetchExchangeBalances(
    { commit, rootGetters },
    payload: ExchangeBalancePayload
  ): Promise<void> {
    const { location, ignoreCache } = payload;
    const isTaskRunning = rootGetters['tasks/isTaskRunning'];
    const taskMetadata = rootGetters['tasks/metadata'];
    const status = rootGetters['status'];
    const taskType = TaskType.QUERY_EXCHANGE_BALANCES;

    const meta: ExchangeMeta = taskMetadata(taskType);

    if (isTaskRunning(taskType) && meta.location === location) {
      return;
    }

    const currentStatus: Status = status(Section.EXCHANGES);
    const section = Section.EXCHANGES;
    const newStatus =
      currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);

    try {
      const { taskId } = await api.queryExchangeBalances(location, ignoreCache);
      const meta: ExchangeMeta = {
        location,
        title: i18n
          .t('actions.balances.exchange_balances.task.title', {
            location
          })
          .toString(),
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
        location: location,
        balances: result
      });
    } catch (e) {
      const message = i18n
        .t('actions.balances.exchange_balances.error.message', {
          location,
          error: e.message
        })
        .toString();
      const title = i18n
        .t('actions.balances.exchange_balances.error.title', {
          location
        })
        .toString();
      notify(message, title, Severity.ERROR, true);
    } finally {
      setStatus(Status.LOADED, section, status, commit);
    }
  },
  async fetchExchangeRates({ commit }): Promise<void> {
    try {
      const { taskId } = await api.getFiatExchangeRates(
        currencies.map(value => value.ticker_symbol)
      );

      const meta: TaskMeta = {
        title: i18n.t('actions.balances.exchange_rates.task.title').toString(),
        ignoreResult: false,
        numericKeys: null
      };

      const type = TaskType.EXCHANGE_RATES;
      const task = createTask(taskId, type, meta);

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<ExchangeRates, ExchangeMeta>(
        type
      );

      commit('usdToFiatExchangeRates', result);
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
  async addExchanges(
    { commit, dispatch },
    exchanges: Exchange[]
  ): Promise<void> {
    commit('connectedExchanges', exchanges);
    for (const exchange of exchanges) {
      await dispatch('fetchExchangeBalances', {
        location: exchange.location,
        ignoreCache: false
      } as ExchangeBalancePayload);
    }
  },

  async fetch({ dispatch }, exchanges: Exchange[]): Promise<void> {
    await dispatch('fetchExchangeRates');
    await dispatch('fetchBalances');

    if (exchanges && exchanges.length > 0) {
      await dispatch('addExchanges', exchanges);
    }
    await dispatch('fetchBlockchainBalances');
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
    { blockchain, payload, modules }: AddAccountsPayload
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
      { address, label, tags }: AccountPayload,
      modules?: SupportedModules[]
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

      if (modules && blockchain === ETH) {
        await dispatch(
          'session/enableModule',
          {
            enable: modules,
            addresses: [address]
          },
          { root: true }
        );
      }

      await dispatch('updateBalances', { chain: blockchain, balances: result });
    };

    const additions = accounts.map(value =>
      addAccount(blockchain, value, modules).catch(() => {})
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

        if (blockchain === ETH && payload.modules) {
          await dispatch(
            'session/enableModule',
            {
              enable: payload.modules,
              addresses: [address]
            },
            { root: true }
          );
        }
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

  async fetchSupportedAssets({ commit, state }, refresh: boolean) {
    if (state.supportedAssets.length > 0 && !refresh) {
      return;
    }
    try {
      const supportedAssets = await api.assets.allAssets();
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

  async fetchManualBalances({ commit, rootGetters: { status } }) {
    const currentStatus: Status = status(Section.MANUAL_BALANCES);
    const section = Section.MANUAL_BALANCES;
    const newStatus =
      currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section, status, commit);

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
    } finally {
      setStatus(Status.LOADED, section, status, commit);
    }
  },

  async addManualBalance(
    { commit, dispatch },
    balance: ManualBalance
  ): Promise<ActionStatus> {
    try {
      const { balances } = await api.balances.addManualBalances([balance]);
      commit('manualBalances', balances);
      dispatch('refreshPrices', false);
      return {
        success: true
      };
    } catch (e) {
      return {
        success: false,
        message: e.message
      };
    }
  },

  async editManualBalance(
    { commit, dispatch },
    balance: ManualBalance
  ): Promise<ActionStatus> {
    try {
      const { balances } = await api.balances.editManualBalances([balance]);
      commit('manualBalances', balances);
      dispatch('refreshPrices', false);
      return {
        success: true
      };
    } catch (e) {
      return {
        success: false,
        message: e.message
      };
    }
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
    { exchange, edit }: ExchangeSetupPayload
  ): Promise<boolean> {
    try {
      const success = await api.setupExchange(exchange, edit);
      const exchangeEntry: Exchange = {
        name: exchange.name,
        location: exchange.location,
        krakenAccountType: exchange.krakenAccountType ?? undefined,
        ftxSubaccount: exchange.ftxSubaccount ?? undefined
      };

      if (!edit) {
        commit('addExchange', exchangeEntry);
      } else {
        commit('editExchange', {
          exchange: exchangeEntry,
          newName: exchange.newName
        });
      }

      dispatch('fetchExchangeBalances', {
        location: exchange.location,
        ignoreCache: false
      } as ExchangeBalancePayload).then(() => dispatch('refreshPrices', false));

      return success;
    } catch (e) {
      showError(
        i18n
          .t('actions.balances.exchange_setup.description', {
            exchange: exchange.location,
            error: e.message
          })
          .toString(),
        i18n.t('actions.balances.exchange_setup.title').toString()
      );
      return false;
    }
  },

  async removeExchange(
    { commit, dispatch, state },
    exchange: Exchange
  ): Promise<boolean> {
    try {
      const success = await api.removeExchange(exchange);
      if (success) {
        const exchangeIndex = state.connectedExchanges.findIndex(
          ({ location, name }) =>
            name === exchange.name && location === exchange.location
        );
        assert(
          exchangeIndex >= 0,
          `${exchange} not found in ${state.connectedExchanges
            .map(exchange => `${exchange.name} on ${exchange.location}`)
            .join(', ')}`
        );
        commit('removeExchange', exchange);

        const remaining = state.connectedExchanges
          .map(({ location }) => location)
          .filter(location => location === exchange.location);

        if (remaining.length > 0) {
          await dispatch('fetchExchangeBalances', {
            location: exchange.location,
            ignoreCache: false
          } as ExchangeBalancePayload);
        }
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
  },

  async fetchHistoricPrice(
    { commit, rootGetters: { 'tasks/isTaskRunning': isTaskRunning } },
    { fromAsset, timestamp, toAsset }: HistoricPricePayload
  ): Promise<BigNumber> {
    const taskType = TaskType.FETCH_HISTORIC_PRICE;
    if (isTaskRunning(taskType)) {
      return bigNumberify(-1);
    }

    try {
      const { taskId } = await api.balances.fetchRate(
        fromAsset,
        toAsset,
        timestamp
      );
      const task = createTask(taskId, taskType, {
        title: i18n
          .t('actions.balances.historic_fetch_price.task.title')
          .toString(),
        description: i18n
          .t('actions.balances.historic_fetch_price.task.description', {
            fromAsset,
            toAsset,
            date: convertFromTimestamp(timestamp)
          })
          .toString(),
        ignoreResult: false,
        numericKeys: null
      });
      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<HistoricPrices, TaskMeta>(
        taskType,
        `${taskId}`
      );
      return result.assets[fromAsset][timestamp];
    } catch (e) {
      return bigNumberify(-1);
    }
  },

  async fetchLoopringBalances(
    { commit, rootGetters: { status }, rootState: { session } },
    refresh: boolean
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(MODULE_LOOPRING)) {
      return;
    }

    const section = Section.L2_LOOPRING_BALANCES;
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
      const taskType = TaskType.L2_LOOPRING;
      const { taskId } = await api.balances.loopring();
      const task = createTask(taskId, taskType, {
        title: i18n.t('actions.balances.loopring.task.title').toString(),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<AccountAssetBalances, TaskMeta>(
        taskType
      );

      commit(MUTATION_UPDATE_LOOPRING_BALANCES, result);
    } catch (e) {
      notify(
        i18n
          .t('actions.balances.loopring.error.description', {
            error: e.message
          })
          .toString(),
        i18n.t('actions.balances.loopring.error.title').toString(),
        Severity.ERROR,
        true
      );
    }
    setStatus(Status.LOADED, section, status, commit);
  },

  async fetchTokenDetails({ commit }, address: string): Promise<ERC20Token> {
    try {
      const taskType = TaskType.ERC20_DETAILS;
      const { taskId } = await api.erc20details(address);
      const task = createTask(taskId, taskType, {
        title: i18n
          .t('actions.assets.erc20.task.title', { address })
          .toString(),
        ignoreResult: false,
        numericKeys: balanceKeys
      });

      commit('tasks/add', task, { root: true });

      const { result } = await taskCompletion<ERC20Token, TaskMeta>(taskType);
      return result;
    } catch (e) {
      notify(
        i18n
          .t('actions.assets.erc20.error.description', {
            message: e.message
          })
          .toString(),
        i18n.t('actions.assets.erc20.error.title', { address }).toString(),
        Severity.ERROR,
        true
      );
      return {};
    }
  }
};
