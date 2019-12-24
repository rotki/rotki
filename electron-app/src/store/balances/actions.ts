import { ActionTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { BalanceState } from '@/store/balances/state';
import { api } from '@/services/rotkehlchen-api';
import { createTask, ExchangeMeta, TaskType } from '@/model/task';
import { Severity, UsdToFiatExchangeRates } from '@/typing/types';
import { notify } from '@/store/notifications/utils';
import { FiatBalance } from '@/model/blockchain-balances';
import { bigNumberify } from '@/utils/bignumbers';
import { convertBalances, convertEthBalances } from '@/utils/conversion';
import { currencies } from '@/data/currencies';

export const actions: ActionTree<BalanceState, RotkehlchenState> = {
  fetchBalances({ commit, rootGetters }): void {
    const isTaskRunning = rootGetters['tasks/isTaskRunning'];
    if (isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES)) {
      return;
    }
    api
      .queryBalancesAsync()
      .then(result => {
        const task = createTask(
          result.task_id,
          TaskType.QUERY_EXCHANGE_BALANCES,
          {
            description: `Query All Balances`,
            ignoreResult: true
          }
        );

        commit('tasks/add', task, { root: true });
      })
      .catch(reason => {
        notify(
          `Failed to fetch all balances: ${reason}`,
          'Querying all Balances',
          Severity.ERROR
        );
      });
  },
  fetchExchangeBalances({ commit }, payload: ExchangeBalancePayload): void {
    const { name } = payload;
    api
      .queryExchangeBalancesAsync(name)
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
  async fetchBlockchainBalances({ commit }): Promise<void> {
    try {
      const result = await api.queryBlockchainBalancesAsync();
      const task = createTask(
        result.task_id,
        TaskType.QUERY_BLOCKCHAIN_BALANCES,
        {
          description: 'Query Blockchain Balances',
          ignoreResult: false
        }
      );
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
        name: exchange
      });
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
    const { per_account, totals } = await api.removeBlockchainAccount(
      blockchain,
      address
    );
    const { ETH, BTC } = per_account;

    if (blockchain === 'ETH') {
      commit('updateEth', convertEthBalances(ETH));
    } else {
      commit('updateBtc', convertBalances(BTC));
    }
    commit('updateTotals', convertBalances(totals));
  },

  async addAccount({ commit }, payload: BlockchainAccountPayload) {
    const { address, blockchain } = payload;
    const { per_account, totals } = await api.addBlockchainAccount(
      blockchain,
      address
    );
    const { ETH, BTC } = per_account;
    if (blockchain === 'ETH') {
      commit('updateEth', convertEthBalances(ETH));
    } else {
      commit('updateBtc', convertBalances(BTC));
    }
    commit('updateTotals', convertBalances(totals));
  }
};

export interface BlockchainAccountPayload {
  readonly address: string;
  readonly blockchain: 'ETH' | 'BTC';
}

export interface ExchangeBalancePayload {
  readonly name: string;
}
