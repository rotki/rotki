import { Module } from 'vuex';
import { TradesState } from '@/store/trades/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const trades: Module<TradesState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
