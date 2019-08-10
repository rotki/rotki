import { ActionTree } from 'vuex';
import store, { RotkehlchenState } from '@/store';
import { BalanceState } from '@/store/balances/state';
import { service } from '@/services/rotkehlchen_service';
import { createTask, TaskType } from '@/model/task';
import { UsdToFiatExchangeRates } from '@/typing/types';
import { notify } from '@/store/notifications/utils';
import { FiatBalance } from '@/model/blockchain-balances';
import { bigNumberify } from '@/utils/bignumbers';

export const actions: ActionTree<BalanceState, RotkehlchenState> = {
  fetchExchangeBalances({ commit }, payload: ExchangeBalancePayload): void {
    const { name, balanceTask } = payload;
    service
      .query_exchange_balances_async(name)
      .then(result => {
        console.log(`Query ${name} returned task id ${result.task_id}`);
        const task = createTask(
          result.task_id,
          TaskType.QUERY_EXCHANGE_BALANCES,
          `Query ${name} Balances`,
          true
        );

        if (balanceTask) {
          commit('tasks/addBalanceTask', task);
        } else {
          commit('task/add', task);
        }
      })
      .catch(reason => {
        console.log(`Error at querying exchange ${name} balances: ${reason}`);
      });
  },
  async fetchExchangeRates({ commit }): Promise<void> {
    try {
      const result = await service.get_fiat_exchange_rates();
      const rates = result.exchange_rates;
      const exchangeRates: UsdToFiatExchangeRates = {};

      for (const asset in rates) {
        if (!rates.hasOwnProperty(asset)) {
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
      console.log(`Blockchain balances returned task id ${result.task_id}`);
      const task = createTask(
        result.task_id,
        TaskType.QUERY_BLOCKCHAIN_BALANCES,
        'Query Blockchain Balances',
        true
      );
      commit('tasks/addBalanceTask', task);
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
    commit('balances/connectedExchanges', exchanges);
    for (const exchange of exchanges) {
      await dispatch(
        'balances/fetchExchangeBalances',
        createExchangePayload(exchange)
      );
    }
  },
  async fetch(
    { dispatch },
    payload: { newUser: boolean; exchanges: string[] }
  ): Promise<void> {
    const { exchanges, newUser } = payload;

    await dispatch('balances/fetchExchangeRates');

    if (exchanges) {
      await dispatch('balances/addExchanges');
    }

    if (!newUser) {
      await dispatch('balances/fetchBlockchainBalances');
      await dispatch('balances/fetchFiatBalances');
    }
  }
};

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
