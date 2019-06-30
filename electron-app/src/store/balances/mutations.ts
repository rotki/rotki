import { MutationTree } from 'vuex';
import { BalanceState } from '@/store/balances/state';
import { Balances, EthBalances } from '@/model/blockchain-balances';

export const mutations: MutationTree<BalanceState> = {
  updateEth(state: BalanceState, payload: EthBalances) {
    state.eth = { ...payload };
  },
  updateBtc(state: BalanceState, payload: Balances) {
    state.btc = { ...payload };
  },
  updateTotals(state: BalanceState, payload: Balances) {
    state.totals = { ...payload };
  }
};
