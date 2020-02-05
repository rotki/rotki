import { mutations } from './mutations';
import { getters } from './getters';
import { actions } from './actions';
import { state, BalanceState } from './state';
import { Module } from 'vuex';
import { RotkehlchenState } from '@/store/store';

const namespaced: boolean = true;

export const balances: Module<BalanceState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
