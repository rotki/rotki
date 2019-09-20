import { MutationTree } from 'vuex';
import { BalanceState } from '@/store/balances/state';
import {
  Balances,
  EthBalances,
  FiatBalance
} from '@/model/blockchain-balances';
import {
  ExchangeData,
  ExchangeInfo,
  UsdToFiatExchangeRates
} from '@/typing/types';

export const mutations: MutationTree<BalanceState> = {
  updateEth(state: BalanceState, payload: EthBalances) {
    state.eth = { ...payload };
  },
  updateBtc(state: BalanceState, payload: Balances) {
    state.btc = { ...payload };
  },
  updateTotals(state: BalanceState, payload: Balances) {
    state.totals = { ...payload };
  },
  usdToFiatExchangeRates(
    state: BalanceState,
    usdToFiatExchangeRates: UsdToFiatExchangeRates
  ) {
    state.usdToFiatExchangeRates = usdToFiatExchangeRates;
  },
  connectedExchanges(state: BalanceState, connectedExchanges: string[]) {
    state.connectedExchanges = connectedExchanges;
  },
  addExchange(state: BalanceState, exchangeName: string) {
    state.connectedExchanges.push(exchangeName);
  },
  removeExchange(state: BalanceState, exchangeName: string) {
    const index = state.connectedExchanges.findIndex(
      value => value === exchangeName
    );
    state.connectedExchanges.splice(index, 1);
  },
  addExchangeBalances(state: BalanceState, data: ExchangeInfo) {
    const update: ExchangeData = {};
    update[data.name] = data.balances;
    state.exchangeBalances = { ...state.exchangeBalances, ...update };
  },
  fiatBalances(state: BalanceState, fiatBalances: FiatBalance[]) {
    state.fiatBalances = [...fiatBalances];
  }
};
