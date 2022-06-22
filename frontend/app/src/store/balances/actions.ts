import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Message, Severity } from '@rotki/common/lib/messages';
import { Eth2Validators } from '@rotki/common/lib/staking/eth2';
import { get } from '@vueuse/core';
import { ActionTree } from 'vuex';
import { currencies, CURRENCY_USD } from '@/data/currencies';
import i18n from '@/i18n';
import {
  Balances,
  BlockchainBalances,
  BtcBalances,
  ManualBalance,
  ManualBalances,
  ManualBalanceWithValue
} from '@/services/balances/types';
import { balanceKeys } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import {
  BtcAccountData,
  GeneralAccountData,
  XpubAccountData
} from '@/services/types-api';
import { BalanceActions } from '@/store/balances/action-types';
import { chainSection } from '@/store/balances/const';
import { useEnsNamesStore } from '@/store/balances/index';
import { BalanceMutations } from '@/store/balances/mutation-types';
import {
  AccountAssetBalances,
  AccountPayload,
  AddAccountsPayload,
  AllBalancePayload,
  AssetBalances,
  AssetPriceResponse,
  AssetPrices,
  BalanceState,
  BasicBlockchainAccountPayload,
  BlockchainAccountPayload,
  BlockchainBalancePayload,
  ERC20Token,
  ExchangeBalancePayload,
  ExchangeSetupPayload,
  FetchPricePayload,
  HistoricPricePayload,
  HistoricPrices,
  NonFungibleBalances,
  OracleCachePayload,
  XpubPayload
} from '@/store/balances/types';
import { Section, Status } from '@/store/const';
import { useHistory } from '@/store/history';
import { useNotifications } from '@/store/notifications';
import { useMainStore } from '@/store/store';
import { useTasks } from '@/store/tasks';
import { ActionStatus, RotkehlchenState } from '@/store/types';
import {
  getStatus,
  getStatusUpdater,
  isLoading,
  setStatus,
  showError
} from '@/store/utils';
import { Writeable } from '@/types';
import { Eth2Validator } from '@/types/balances';
import { Exchange } from '@/types/exchanges';
import { Module } from '@/types/modules';
import { BlockchainMetadata, ExchangeMeta, TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { ExchangeRates } from '@/types/user';
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';
import { chunkArray } from '@/utils/data';
import { convertFromTimestamp } from '@/utils/date';
import { logger } from '@/utils/logging';

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
  async fetchBalances({ dispatch }, payload: Partial<AllBalancePayload> = {}) {
    const { addTask, isTaskRunning } = useTasks();
    if (get(isTaskRunning(TaskType.QUERY_BALANCES))) {
      return;
    }
    try {
      const { taskId } = await api.queryBalancesAsync(payload);
      await addTask(taskId, TaskType.QUERY_BALANCES, {
        title: i18n.t('actions.balances.all_balances.task.title').toString(),
        ignoreResult: true
      });
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.balances.all_balances.error.title').toString(),
        message: i18n
          .t('actions.balances.all_balances.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
    }
    await dispatch('accounts');
  },

  async fetchConnectedExchangeBalances(
    { dispatch, state: { connectedExchanges: exchanges } },
    refresh: boolean = false
  ): Promise<void> {
    for (const exchange of exchanges) {
      await dispatch('fetchExchangeBalances', {
        location: exchange.location,
        ignoreCache: refresh
      } as ExchangeBalancePayload);
    }
  },

  async fetchExchangeBalances(
    { commit },
    payload: ExchangeBalancePayload
  ): Promise<void> {
    const { location, ignoreCache } = payload;
    const taskType = TaskType.QUERY_EXCHANGE_BALANCES;

    const { awaitTask, isTaskRunning, metadata } = useTasks();
    const meta = metadata<ExchangeMeta>(taskType);

    if (get(isTaskRunning(taskType)) && meta?.location === location) {
      return;
    }

    const currentStatus: Status = getStatus(Section.EXCHANGES);
    const section = Section.EXCHANGES;
    const newStatus =
      currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const { taskId } = await api.queryExchangeBalances(location, ignoreCache);
      const meta: ExchangeMeta = {
        location,
        title: i18n
          .t('actions.balances.exchange_balances.task.title', {
            location
          })
          .toString(),
        numericKeys: balanceKeys
      };

      const { result } = await awaitTask<AssetBalances, ExchangeMeta>(
        taskId,
        taskType,
        meta,
        true
      );

      commit('addExchangeBalances', {
        location: location,
        balances: result
      });
    } catch (e: any) {
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
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    } finally {
      setStatus(Status.LOADED, section);
    }
  },
  async fetchExchangeRates({ commit }): Promise<void> {
    try {
      const { taskId } = await api.getFiatExchangeRates(
        currencies.map(value => value.tickerSymbol)
      );

      const meta: TaskMeta = {
        title: i18n.t('actions.balances.exchange_rates.task.title').toString(),
        numericKeys: []
      };

      const { awaitTask } = useTasks();
      const { result } = await awaitTask<ExchangeRates, TaskMeta>(
        taskId,
        TaskType.EXCHANGE_RATES,
        meta
      );

      commit('usdToFiatExchangeRates', ExchangeRates.parse(result));
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.balances.exchange_rates.error.title').toString(),
        message: i18n
          .t('actions.balances.exchange_rates.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
    }
  },
  async fetchBlockchainBalances(
    { dispatch },
    payload: BlockchainBalancePayload = {
      ignoreCache: false
    }
  ): Promise<void> {
    const { awaitTask } = useTasks();
    const { blockchain, ignoreCache } = payload;

    const chains: Blockchain[] = [];
    if (!blockchain) {
      chains.push(...Object.values(Blockchain));
    } else {
      chains.push(blockchain);
    }

    const fetch: (chain: Blockchain) => Promise<void> = async (
      chain: Blockchain
    ) => {
      const section = chainSection[chain];
      const currentStatus = getStatus(section);

      if (isLoading(currentStatus)) {
        return;
      }

      const newStatus =
        currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
      setStatus(newStatus, section);

      const { taskId } = await api.balances.queryBlockchainBalances(
        ignoreCache,
        chain
      );
      const taskType = TaskType.QUERY_BLOCKCHAIN_BALANCES;
      const { result } = await awaitTask<
        BlockchainBalances,
        BlockchainMetadata
      >(
        taskId,
        taskType,
        {
          chain,
          title: `Query ${chain} Balances`,
          numericKeys: []
        } as BlockchainMetadata,
        true
      );
      const balances = BlockchainBalances.parse(result);
      await dispatch('updateBalances', {
        chain,
        balances,
        ignoreCache
      });
      setStatus(Status.LOADED, section);
    };
    try {
      await Promise.all(chains.map(fetch));
    } catch (e: any) {
      logger.error(e);
      const message = i18n.tc(
        'actions.balances.blockchain.error.description',
        0,
        {
          error: e.message
        }
      );
      const { notify } = useNotifications();
      notify({
        title: i18n.tc('actions.balances.blockchain.error.title'),
        message,
        display: true
      });
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
      const { purgeHistoryLocation } = useHistory();
      purgeHistoryLocation(exchange.location).then();
    }
  },

  async fetch({ dispatch }, exchanges: Exchange[]): Promise<void> {
    await dispatch('fetchExchangeRates');
    await dispatch('fetchBalances');

    if (exchanges && exchanges.length > 0) {
      await dispatch('addExchanges', exchanges);
    }
    await dispatch('fetchBlockchainBalances');
    await dispatch(BalanceActions.FETCH_NF_BALANCES);
  },

  async updateBalances(
    { commit, dispatch },
    payload: {
      chain?: Blockchain;
      balances: BlockchainBalances;
      ignoreCache?: boolean;
    }
  ): Promise<void> {
    const { perAccount, totals } = payload.balances;
    const {
      ETH: ethBalances,
      ETH2: eth2Balances,
      BTC: btcBalances,
      BCH: bchBalances,
      KSM: ksmBalances,
      DOT: dotBalances,
      AVAX: avaxBalances
    } = perAccount;
    const chain = payload.chain;
    const forceUpdate = payload.ignoreCache;

    if (forceUpdate && (ethBalances || eth2Balances)) {
      const addresses = [];
      if (ethBalances) {
        addresses.push(...Object.keys(ethBalances));
      }
      if (eth2Balances) {
        addresses.push(...Object.keys(eth2Balances));
      }

      const { fetchEnsNames } = useEnsNamesStore();
      fetchEnsNames(addresses, forceUpdate);
    }

    if (!chain || chain === Blockchain.ETH) {
      commit('updateEth', ethBalances ?? {});
    }

    if (!chain || chain === Blockchain.KSM) {
      commit('updateKsm', ksmBalances ?? {});
    }

    if (!chain || chain === Blockchain.DOT) {
      commit('updateDot', dotBalances ?? {});
    }

    if (!chain || chain === Blockchain.BTC) {
      commit('updateBtc', btcBalances ?? {});
    }

    if (!chain || chain === Blockchain.BCH) {
      commit('updateBch', bchBalances ?? {});
    }

    if (!chain || chain === Blockchain.AVAX) {
      commit('updateAvax', avaxBalances ?? {});
    }

    if (!chain || chain === Blockchain.ETH2) {
      commit('updateEth2', eth2Balances ?? {});
    }

    commit('updateTotals', totals.assets);
    commit('updateLiabilities', totals.liabilities);
    const blockchainToRefresh = chain ? [chain] : null;
    dispatch('accounts', blockchainToRefresh).then();
  },

  async deleteXpub({ dispatch }, payload: XpubPayload) {
    const { awaitTask, isTaskRunning } = useTasks();
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      if (get(isTaskRunning(taskType))) {
        return;
      }
      const { taskId } = await api.deleteXpub(payload);
      const { result } = await awaitTask<
        BlockchainBalances,
        BlockchainMetadata
      >(taskId, taskType, {
        title: i18n.tc('actions.balances.xpub_removal.task.title'),
        description: i18n.tc(
          'actions.balances.xpub_removal.task.description',
          0,
          {
            xpub: payload.xpub
          }
        ),
        blockchain: payload.blockchain,
        numericKeys: []
      } as BlockchainMetadata);
      const balances = BlockchainBalances.parse(result);
      await dispatch('updateBalances', {
        chain: payload.blockchain,
        balances
      });
    } catch (e: any) {
      logger.error(e);
      const title = i18n.tc('actions.balances.xpub_removal.error.title');
      const description = i18n.tc(
        'actions.balances.xpub_removal.error.description',
        0,
        {
          xpub: payload.xpub,
          error: e.message
        }
      );
      const { notify } = useNotifications();
      notify({
        title,
        message: description,
        display: true
      });
    }
  },

  async removeAccount(
    { commit, dispatch },
    payload: BasicBlockchainAccountPayload
  ) {
    const { accounts, blockchain } = payload;
    assert(accounts, 'Accounts was empty');
    const { taskId } = await api.removeBlockchainAccount(blockchain, accounts);
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.REMOVE_ACCOUNT;
      const { result } = await awaitTask<
        BlockchainBalances,
        BlockchainMetadata
      >(taskId, taskType, {
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
        numericKeys: []
      } as BlockchainMetadata);

      const balances = BlockchainBalances.parse(result);

      commit('defi/reset', undefined, { root: true });
      dispatch(BalanceActions.FETCH_NF_BALANCES);
      await dispatch('updateBalances', { chain: blockchain, balances });
      useMainStore().resetDefiStatus();
      await dispatch('refreshPrices', { ignoreCache: false });
    } catch (e: any) {
      logger.error(e);
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
      const { notify } = useNotifications();
      notify({
        title,
        message: description,
        display: true
      });
    }
  },

  async addAccounts(
    { state, commit, dispatch },
    { blockchain, payload, modules }: AddAccountsPayload
  ): Promise<void> {
    const { awaitTask, isTaskRunning } = useTasks();
    const taskType = TaskType.ADD_ACCOUNT;
    if (get(isTaskRunning(taskType))) {
      return;
    }

    let existingAccounts: GeneralAccountData[];
    if (blockchain === Blockchain.ETH) {
      existingAccounts = state.ethAccounts;
    } else if (blockchain === Blockchain.AVAX) {
      existingAccounts = state.avaxAccounts;
    } else if (blockchain === Blockchain.DOT) {
      existingAccounts = state.dotAccounts;
    } else if (blockchain === Blockchain.KSM) {
      existingAccounts = state.ksmAccounts;
    } else {
      throw new Error(
        `this chain ${blockchain} doesn't support multiple address addition`
      );
    }
    const existingAddresses = existingAccounts.map(address =>
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
      const { notify } = useNotifications();
      notify({
        title,
        message: description,
        severity: Severity.INFO,
        display: true
      });
      return;
    }

    const addAccount = async (
      blockchain: Blockchain,
      { address, label, tags }: AccountPayload,
      modules?: Module[]
    ) => {
      try {
        const { taskId } = await api.addBlockchainAccount({
          blockchain,
          address,
          label,
          tags
        });

        const { result } = await awaitTask<
          BlockchainBalances,
          BlockchainMetadata
        >(
          taskId,
          taskType,
          {
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
            numericKeys: []
          } as BlockchainMetadata,
          true
        );

        if (modules && blockchain === Blockchain.ETH) {
          await dispatch(
            'session/enableModule',
            {
              enable: modules,
              addresses: [address]
            },
            { root: true }
          );
        }

        const balances = BlockchainBalances.parse(result);

        await dispatch('updateBalances', { chain: blockchain, balances });
      } catch (e) {
        logger.error(e);
      }
    };

    const requests = accounts.map(value =>
      addAccount(blockchain, value, modules)
    );

    try {
      await Promise.allSettled(requests);
      const options = { root: true };
      if (blockchain === Blockchain.ETH) {
        await dispatch('fetchBlockchainBalances', {
          blockchain: Blockchain.ETH2
        });
      }
      commit('defi/reset', undefined, options);
      dispatch(BalanceActions.FETCH_NF_BALANCES);
      useMainStore().resetDefiStatus();
      await dispatch('refreshPrices', { ignoreCache: false });
    } catch (e: any) {
      logger.error(e);
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
      const { notify } = useNotifications();
      notify({
        title,
        message: description,
        display: true
      });
    }
  },

  async addAccount({ commit, dispatch }, payload: BlockchainAccountPayload) {
    const { awaitTask } = useTasks();
    const { address, blockchain } = payload;
    const taskType = TaskType.ADD_ACCOUNT;
    const { taskId } = await api.addBlockchainAccount(payload);

    const { result } = await awaitTask<BlockchainBalances, BlockchainMetadata>(
      taskId,
      taskType,
      {
        title: i18n.tc(
          'actions.balances.blockchain_account_add.task.title',
          0,
          {
            blockchain
          }
        ),
        description: i18n.tc(
          'actions.balances.blockchain_account_add.task.description',
          0,
          { address }
        ),
        blockchain,
        numericKeys: []
      } as BlockchainMetadata
    );

    try {
      const balances = BlockchainBalances.parse(result);
      await dispatch('updateBalances', {
        chain: blockchain,
        balances: balances
      });

      if (blockchain === Blockchain.ETH && payload.modules) {
        await dispatch(
          'session/enableModule',
          {
            enable: payload.modules,
            addresses: [address]
          },
          { root: true }
        );
      }

      if (blockchain === Blockchain.ETH) {
        await dispatch('fetchBlockchainBalances', {
          blockchain: Blockchain.ETH2
        });
      }
      commit('defi/reset', undefined, { root: true });
      dispatch(BalanceActions.FETCH_NF_BALANCES);
      useMainStore().resetDefiStatus();
      await dispatch('refreshPrices', { ignoreCache: false });
    } catch (e: any) {
      logger.error(e);
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
      const { notify } = useNotifications();
      notify({
        title,
        message: description,
        display: true
      });
    }
  },

  async editAccount({ commit }, payload: BlockchainAccountPayload) {
    const { blockchain } = payload;
    const isBtc = blockchain === Blockchain.BTC;
    const isBch = blockchain === Blockchain.BCH;
    if (isBtc || isBch) {
      const accountData = await api.editBtcAccount(payload, blockchain);
      if (isBtc) {
        commit('btcAccounts', accountData);
      } else {
        commit('bchAccounts', accountData);
      }
    } else {
      const accountData = await api.editAccount(payload);

      if (blockchain === Blockchain.ETH) {
        commit('ethAccounts', accountData);
      } else if (blockchain === Blockchain.KSM) {
        commit('ksmAccounts', accountData);
      } else if (blockchain === Blockchain.DOT) {
        commit('dotAccounts', accountData);
      } else if (blockchain === Blockchain.AVAX) {
        commit('avaxAccounts', accountData);
      }
    }
  },

  async accounts(
    { commit, rootState: { session } },
    blockchains: Blockchain[] | null
  ) {
    const error = (error: any, blockchain: Blockchain) => {
      logger.error(error);
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.get_accounts.error.title').toString(),
        message: i18n
          .t('actions.get_accounts.error.description', {
            blockchain: Blockchain[blockchain],
            message: error.message
          })
          .toString(),
        display: true
      });
    };
    const getAccounts = async (
      blockchain: Exclude<
        Blockchain,
        Blockchain.BTC | Blockchain.BCH | Blockchain.ETH2
      >
    ) => {
      try {
        const accounts = await api.accounts(blockchain);
        if (blockchain === Blockchain.ETH) {
          commit('ethAccounts', accounts);

          const addresses = accounts.map(account => account.address);
          const { fetchEnsNames } = useEnsNamesStore();
          fetchEnsNames(addresses, true);
        } else if (blockchain === Blockchain.KSM) {
          commit('ksmAccounts', accounts);
        } else if (blockchain === Blockchain.DOT) {
          commit('dotAccounts', accounts);
        } else if (blockchain === Blockchain.AVAX) {
          commit('avaxAccounts', accounts);
        } else {
          throw Error(`invalid argument ${Blockchain[blockchain]}`);
        }
      } catch (e) {
        error(e, blockchain);
      }
    };

    const getBtcAccounts = async (
      blockchain: Blockchain.BTC | Blockchain.BCH
    ) => {
      try {
        const accounts = await api.btcAccounts(blockchain);
        commit(
          blockchain === Blockchain.BTC ? 'btcAccounts' : 'bchAccounts',
          accounts
        );
      } catch (e) {
        error(e, blockchain);
      }
    };

    const getEth2Validators = async () => {
      const { activeModules } = session!.generalSettings;
      if (!activeModules.includes(Module.ETH2)) {
        return;
      }
      try {
        const validators = await api.balances.getEth2Validators();
        commit('eth2Validators', validators);
      } catch (e: any) {
        error(e, Blockchain.ETH2);
      }
    };

    const requests: Promise<void>[] = [];

    const addRequest = <T extends Blockchain>(
      blockchain: T,
      getRequest: (blockchain: T) => Promise<void>
    ) => {
      if (
        !blockchains ||
        blockchains.length === 0 ||
        blockchains.includes(blockchain)
      ) {
        requests.push(getRequest(blockchain));
      }
    };

    addRequest(Blockchain.ETH, chain => getAccounts(chain));
    addRequest(Blockchain.ETH2, () => getEth2Validators());
    addRequest(Blockchain.BTC, chain => getBtcAccounts(chain));
    addRequest(Blockchain.BCH, chain => getBtcAccounts(chain));
    addRequest(Blockchain.KSM, chain => getAccounts(chain));
    addRequest(Blockchain.DOT, chain => getAccounts(chain));
    addRequest(Blockchain.AVAX, chain => getAccounts(chain));

    await Promise.allSettled(requests);
  },
  /* Remove a tag from all accounts of the state */
  async removeTag({ commit, state }, tagName: string) {
    // Other Network
    ['ethAccounts', 'ksmAccounts', 'dotAccounts', 'avaxAccounts'].forEach(
      stateName => {
        const accounts = state[
          stateName as keyof BalanceState
        ] as GeneralAccountData[];
        removeTags(accounts, tagName);
      }
    );

    // Bitcoin Network
    ['btcAccounts', 'bchAccounts'].forEach(stateName => {
      const accounts = state[stateName as keyof BalanceState] as BtcAccountData;
      const standalone = removeTags(accounts.standalone, tagName);

      const xpubs: XpubAccountData[] = [];

      for (let i = 0; i < accounts.xpubs.length; i++) {
        const xpub = accounts.xpubs[i];
        xpubs.push({
          ...xpub,
          tags: removeTag(xpub.tags, tagName),
          addresses: xpub.addresses ? removeTags(xpub.addresses, tagName) : null
        });
      }

      commit(stateName, {
        standalone,
        xpubs
      });
    });
  },
  async fetchNetvalueData({ commit, rootState: { session, settings } }) {
    if (!session?.premium) {
      return;
    }
    try {
      const includeNfts = settings?.nftsInNetValue ?? true;
      const netvalueData = await api.queryNetvalueData(includeNfts);
      commit('netvalueData', netvalueData);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.balances.net_value.error.title').toString(),
        message: i18n
          .t('actions.balances.net_value.error.message', { message: e.message })
          .toString(),
        display: false
      });
    }
  },

  async fetchManualBalances({ commit }) {
    const { awaitTask } = useTasks();
    const currentStatus: Status = getStatus(Section.MANUAL_BALANCES);
    const section = Section.MANUAL_BALANCES;
    const newStatus =
      currentStatus === Status.LOADED ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);

    try {
      const taskType = TaskType.MANUAL_BALANCES;
      const { taskId } = await api.balances.manualBalances();
      const { result } = await awaitTask<ManualBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.tc('actions.manual_balances.task.title'),
          numericKeys: balanceKeys
        }
      );

      commit('manualBalances', result.balances);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n
          .t('actions.balances.manual_balances.error.title')
          .toString(),
        message: i18n
          .t('actions.balances.manual_balances.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
    } finally {
      setStatus(Status.LOADED, section);
    }
  },

  async addManualBalance(
    { commit, dispatch },
    balance: ManualBalance
  ): Promise<ActionStatus> {
    try {
      const { balances } = await api.balances.addManualBalances([balance]);
      commit('manualBalances', balances);
      dispatch('refreshPrices', {
        ignoreCache: false,
        selectedAsset: balance.asset
      });
      return {
        success: true
      };
    } catch (e: any) {
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
      dispatch('refreshPrices', { ignoreCache: false });
      return {
        success: true
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  },

  async deleteManualBalance({ commit }, id: number) {
    try {
      const { balances } = await api.balances.deleteManualBalances([id]);
      commit('manualBalances', balances);
    } catch (e: any) {
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
      } as ExchangeBalancePayload).then(() =>
        dispatch('refreshPrices', { ignoreCache: false })
      );

      return success;
    } catch (e: any) {
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

      const { purgeHistoryLocation } = useHistory();
      await purgeHistoryLocation(exchange.location);

      return success;
    } catch (e: any) {
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
    const manualBalances = [
      ...state.manualBalances,
      ...state.manualLiabilities
    ];
    const totals = { ...state.totals };
    const eth = { ...state.eth };
    const btc: BtcBalances = {
      standalone: state.btc.standalone ? { ...state.btc.standalone } : {},
      xpubs: state.btc.xpubs ? [...state.btc.xpubs] : []
    };
    const bch: BtcBalances = {
      standalone: state.bch.standalone ? { ...state.bch.standalone } : {},
      xpubs: state.bch.xpubs ? [...state.bch.xpubs] : []
    };
    const kusama = { ...state.ksm };
    const polkadot = { ...state.dot };
    const avalanche = { ...state.avax };

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

    const btcPrice = prices[Blockchain.BTC];
    if (btcPrice) {
      for (const address in btc.standalone) {
        const balance = btc.standalone[address];
        btc.standalone[address] = {
          amount: balance.amount,
          usdValue: balance.amount.times(btcPrice)
        };
      }
      const xpubs = btc.xpubs;
      if (xpubs) {
        for (let i = 0; i < xpubs.length; i++) {
          const xpub = xpubs[i];
          for (const address in xpub.addresses) {
            const balance = xpub.addresses[address];
            xpub.addresses[address] = {
              amount: balance.amount,
              usdValue: balance.amount.times(btcPrice)
            };
          }
        }
      }
    }

    commit('updateBtc', btc);

    const bchPrice = prices[Blockchain.BCH];
    if (bchPrice) {
      for (const address in bch.standalone) {
        const balance = bch.standalone[address];
        bch.standalone[address] = {
          amount: balance.amount,
          usdValue: balance.amount.times(bchPrice)
        };
      }
      const xpubs = bch.xpubs;
      if (xpubs) {
        for (let i = 0; i < xpubs.length; i++) {
          const xpub = xpubs[i];
          for (const address in xpub.addresses) {
            const balance = xpub.addresses[address];
            xpub.addresses[address] = {
              amount: balance.amount,
              usdValue: balance.amount.times(bchPrice)
            };
          }
        }
      }
    }

    commit('updateBch', bch);

    for (const address in kusama) {
      const balances = kusama[address];
      kusama[address] = {
        assets: updateBalancePrice(balances.assets, prices),
        liabilities: updateBalancePrice(balances.liabilities, prices)
      };
    }

    commit('updateKsm', kusama);

    for (const address in avalanche) {
      const balances = avalanche[address];
      avalanche[address] = {
        assets: updateBalancePrice(balances.assets, prices),
        liabilities: updateBalancePrice(balances.liabilities, prices)
      };
    }

    commit('updateAvax', avalanche);

    for (const address in polkadot) {
      const balances = polkadot[address];
      polkadot[address] = {
        assets: updateBalancePrice(balances.assets, prices),
        liabilities: updateBalancePrice(balances.liabilities, prices)
      };
    }

    commit('updateDot', polkadot);

    for (const exchange in exchanges) {
      exchanges[exchange] = updateBalancePrice(exchanges[exchange], prices);
    }

    commit('updateExchangeBalances', exchanges);
  },

  async fetchPrices(
    { state, commit, rootGetters: { 'balances/aggregatedAssets': assets } },
    payload: FetchPricePayload
  ): Promise<void> {
    const { awaitTask, isTaskRunning } = useTasks();
    const taskType = TaskType.UPDATE_PRICES;
    if (get(isTaskRunning(taskType))) {
      return;
    }
    const fetchPrices: (assets: string[]) => Promise<void> = async assets => {
      const { taskId } = await api.balances.prices(
        payload.selectedAsset ? [payload.selectedAsset] : assets,
        CURRENCY_USD,
        payload.ignoreCache
      );
      const { result } = await awaitTask<AssetPriceResponse, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.t('actions.session.fetch_prices.task.title').toString(),
          numericKeys: null
        },
        true
      );

      commit(BalanceMutations.UPDATE_PRICES, {
        ...state.prices,
        ...result.assets
      });
    };

    try {
      await Promise.all(
        chunkArray<string>(assets, 100).map(value => fetchPrices(value))
      );
    } catch (e: any) {
      const title = i18n
        .t('actions.session.fetch_prices.error.title')
        .toString();
      const message = i18n
        .t('actions.session.fetch_prices.error.message', {
          error: e.message
        })
        .toString();
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }
  },

  async refreshPrices(
    { dispatch, state },
    payload: FetchPricePayload
  ): Promise<void> {
    setStatus(Status.LOADING, Section.PRICES);
    await dispatch('fetchExchangeRates');
    await dispatch('fetchPrices', payload);
    await dispatch('updatePrices', state.prices);
    setStatus(Status.LOADED, Section.PRICES);
  },

  async createOracleCache(
    _,
    { fromAsset, purgeOld, source, toAsset }: OracleCachePayload
  ): Promise<ActionStatus> {
    const { awaitTask, isTaskRunning } = useTasks();
    const taskType = TaskType.CREATE_PRICE_CACHE;
    if (get(isTaskRunning(taskType))) {
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
      const { result } = await awaitTask<true, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n
            .t('actions.balances.create_oracle_cache.task', {
              fromAsset,
              toAsset,
              source
            })
            .toString(),
          numericKeys: null
        },
        true
      );

      return {
        success: result
      };
    } catch (e: any) {
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
    _,
    { fromAsset, timestamp, toAsset }: HistoricPricePayload
  ): Promise<BigNumber> {
    const { awaitTask, isTaskRunning } = useTasks();
    const taskType = TaskType.FETCH_HISTORIC_PRICE;
    if (get(isTaskRunning(taskType))) {
      return bigNumberify(-1);
    }

    try {
      const { taskId } = await api.balances.fetchRate(
        fromAsset,
        toAsset,
        timestamp
      );
      const { result } = await awaitTask<HistoricPrices, TaskMeta>(
        taskId,
        taskType,
        {
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
          numericKeys: null
        },
        true
      );

      return result.assets[fromAsset][timestamp];
    } catch (e) {
      return bigNumberify(-1);
    }
  },

  async fetchLoopringBalances(
    { commit, rootState: { session } },
    refresh: boolean
  ) {
    const { activeModules } = session!.generalSettings;
    if (!activeModules.includes(Module.LOOPRING)) {
      return;
    }

    const section = Section.L2_LOOPRING_BALANCES;
    const currentStatus = getStatus(section);

    if (
      isLoading(currentStatus) ||
      (currentStatus === Status.LOADED && !refresh)
    ) {
      return;
    }

    const newStatus = refresh ? Status.REFRESHING : Status.LOADING;
    setStatus(newStatus, section);
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.L2_LOOPRING;
      const { taskId } = await api.balances.loopring();
      const { result } = await awaitTask<AccountAssetBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.t('actions.balances.loopring.task.title').toString(),
          numericKeys: balanceKeys
        }
      );

      commit(BalanceMutations.UPDATE_LOOPRING_BALANCES, result);
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.balances.loopring.error.title').toString(),
        message: i18n
          .t('actions.balances.loopring.error.description', {
            error: e.message
          })
          .toString(),
        display: true
      });
    }
    setStatus(Status.LOADED, section);
  },

  async fetchTokenDetails(_, address: string): Promise<ERC20Token> {
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.ERC20_DETAILS;
      const { taskId } = await api.erc20details(address);
      const { result } = await awaitTask<ERC20Token, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n
            .t('actions.assets.erc20.task.title', { address })
            .toString(),
          numericKeys: balanceKeys
        }
      );
      return result;
    } catch (e: any) {
      const { notify } = useNotifications();
      notify({
        title: i18n
          .t('actions.assets.erc20.error.title', { address })
          .toString(),
        message: i18n
          .t('actions.assets.erc20.error.description', {
            message: e.message
          })
          .toString(),
        display: true
      });
      return {};
    }
  },

  async [BalanceActions.FETCH_NF_BALANCES](
    { commit, rootState: { session } },
    payload?: { ignoreCache: boolean }
  ): Promise<void> {
    const { awaitTask } = useTasks();
    const { activeModules } = session!!.generalSettings;
    if (!activeModules.includes(Module.NFTS)) {
      return;
    }
    const section = Section.NON_FUNGIBLE_BALANCES;
    try {
      setStatus(Status.LOADING, section);
      const taskType = TaskType.NF_BALANCES;
      const { taskId } = await api.balances.fetchNfBalances(payload);
      const { result } = await awaitTask<NonFungibleBalances, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.t('actions.nft_balances.task.title').toString(),
          numericKeys: []
        }
      );

      commit(
        BalanceMutations.UPDATE_NF_BALANCES,
        NonFungibleBalances.parse(result)
      );
      setStatus(Status.LOADED, section);
    } catch (e: any) {
      logger.error(e);
      const { notify } = useNotifications();
      notify({
        title: i18n.t('actions.nft_balances.error.title').toString(),
        message: i18n
          .t('actions.nft_balances.error.message', {
            message: e.message
          })
          .toString(),
        display: true
      });
      setStatus(Status.NONE, section);
    }
  },
  async addEth2Validator(
    { dispatch, rootState: { session } },
    payload: Eth2Validator
  ) {
    assert(session);
    const { awaitTask } = useTasks();
    const { activeModules } = session.generalSettings;
    if (!activeModules.includes(Module.ETH2)) {
      return;
    }
    const id = payload.publicKey || payload.validatorIndex;
    try {
      const taskType = TaskType.ADD_ETH2_VALIDATOR;
      const { taskId } = await api.balances.addEth2Validator(payload);
      const { result } = await awaitTask<Boolean, TaskMeta>(taskId, taskType, {
        title: i18n.t('actions.add_eth2_validator.task.title').toString(),
        description: i18n
          .t('actions.add_eth2_validator.task.description', { id })
          .toString(),
        numericKeys: []
      });
      if (result) {
        const { resetStatus } = getStatusUpdater(Section.STAKING_ETH2);
        await dispatch('fetchBlockchainBalances', {
          blockchain: Blockchain.ETH2,
          ignoreCache: true
        });
        resetStatus();
        resetStatus(Section.STAKING_ETH2_DEPOSITS);
        resetStatus(Section.STAKING_ETH2_STATS);
      }

      return result;
    } catch (e: any) {
      logger.error(e);
      const { setMessage } = useMainStore();
      setMessage({
        description: i18n
          .t('actions.add_eth2_validator.error.description', {
            id,
            message: e.message
          })
          .toString(),
        title: i18n.t('actions.add_eth2_validator.error.title').toString(),
        success: false
      });
      return false;
    }
  },
  async editEth2Validator(
    { dispatch, rootState: { session } },
    payload: Eth2Validator
  ) {
    assert(session);
    const { activeModules } = session.generalSettings;
    if (!activeModules.includes(Module.ETH2)) {
      return;
    }

    const id = payload.validatorIndex;
    try {
      const success = await api.balances.editEth2Validator(payload);

      if (success) {
        const { resetStatus } = getStatusUpdater(Section.STAKING_ETH2);
        await dispatch('fetchBlockchainBalances', {
          blockchain: Blockchain.ETH2,
          ignoreCache: true
        });
        resetStatus();
        resetStatus(Section.STAKING_ETH2_DEPOSITS);
        resetStatus(Section.STAKING_ETH2_STATS);
      }

      return success;
    } catch (e: any) {
      const { setMessage } = useMainStore();
      logger.error(e);
      const message: Message = {
        description: i18n
          .t('actions.edit_eth2_validator.error.description', {
            id,
            message: e.message
          })
          .toString(),
        title: i18n.t('actions.edit_eth2_validator.error.title').toString(),
        success: false
      };
      await setMessage(message);
      return false;
    }
  },
  async deleteEth2Validators({ state, commit }, validators: string) {
    const { setMessage } = useMainStore();
    try {
      const entries = [...state.eth2Validators.entries];
      const eth2Validators = entries.filter(({ publicKey }) =>
        validators.includes(publicKey)
      );
      const success = await api.balances.deleteEth2Validators(eth2Validators);
      if (success) {
        const remainingValidators = entries.filter(
          ({ publicKey }) => !validators.includes(publicKey)
        );
        const data: Eth2Validators = {
          entriesLimit: state.eth2Validators.entriesLimit,
          entriesFound: remainingValidators.length,
          entries: remainingValidators
        };
        commit('eth2Validators', data);
        const balances = { ...state.eth2 };
        for (const validator of validators) {
          delete balances[validator];
        }
        commit('updateEth2', balances);
      }
      return success;
    } catch (e: any) {
      logger.error(e);
      setMessage({
        description: i18n
          .t('actions.delete_eth2_validator.error.description', {
            message: e.message
          })
          .toString(),
        title: i18n.t('actions.delete_eth2_validator.error.title').toString(),
        success: false
      });
      return false;
    }
  }
};
