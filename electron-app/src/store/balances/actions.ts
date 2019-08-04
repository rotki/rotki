import { ActionTree } from 'vuex';
import { RotkehlchenState } from '@/store';
import { BalanceState } from '@/store/balances/state';

export const actions: ActionTree<BalanceState, RotkehlchenState> = {
  consume({ commit, getters }): any {}
};
