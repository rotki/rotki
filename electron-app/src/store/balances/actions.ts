import { ActionTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { BalanceState } from '@/store/balances/state';
import { service } from '@/services/rotkehlchen_service';
import { createTask, TaskType } from '@/model/task';
import { Severity, UsdToFiatExchangeRates } from '@/typing/types';
import { notify } from '@/store/notifications/utils';
import { FiatBalance } from '@/model/blockchain-balances';
import { bigNumberify } from '@/utils/bignumbers';
import { convertBalances, convertEthBalances } from '@/utils/conversion';

export const actions: ActionTree<BalanceState, RotkehlchenState> = {
  fetchExchangeBalances({ commit }, payload: ExchangeBalancePayload): void {
    const { name, balanceTask } = payload;
    service
      .query_exchange_balances_async(name)
      .then(result => {
        const task = createTask(
          result.task_id,
          TaskType.QUERY_EXCHANGE_BALANCES,
          `Query ${name} Balances`,
          true
        );

        if (balanceTask) {
          commit('tasks/addBalanceTask', task, { root: true });
        } else {
          commit('tasks/add', task, { root: true });
        }
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
      const result = await service.get_fiat_exchange_rates();
      const rates = result.exchange_rates;
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
      const result = await service.query_blockchain_balances_async();
      const task = createTask(
        result.task_id,
        TaskType.QUERY_BLOCKCHAIN_BALANCES,
        'Query Blockchain Balances',
        true
      );
      commit('tasks/addBalanceTask', task, { root: true });
    } catch (e) {
      notify(
        `Error at querying blockchain balances: ${e}`,
        'Querying blockchain balances'
      );
    }
  },
  async fetchFiatBalances({ commit }): Promise<void> {
    try {
      const result = await service.query_fiat_balances();
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
      await dispatch('fetchExchangeBalances', createExchangePayload(exchange));
    }
  },
  async fetch(
    { dispatch },
    payload: { newUser: boolean; exchanges: string[] }
  ): Promise<void> {
    const { exchanges, newUser } = payload;

    await dispatch('fetchExchangeRates');

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
    const { per_account, totals } = await service.remove_blockchain_account(
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
    const { per_account, totals } = await service.add_blockchain_account(
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
  readonly balanceTask: boolean;
}

export const createExchangePayload: (
  name: string,
  balanceTask?: boolean
) => ExchangeBalancePayload = (name, balanceTask = false) => ({
  name,
  balanceTask
});
