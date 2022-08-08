import { Module } from 'vuex';
import { BalanceState } from '@/store/balances/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const balances: Module<BalanceState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
