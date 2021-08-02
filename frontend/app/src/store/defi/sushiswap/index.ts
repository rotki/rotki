import { Module } from 'vuex';
import { SushiswapState } from '@/store/defi/sushiswap/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const sushiswap: Module<SushiswapState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
