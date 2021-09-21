import { Module } from 'vuex';
import { liquity } from '@/store/defi/liquity';
import { sushiswap } from '@/store/defi/sushiswap';
import { DefiState } from '@/store/defi/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const defi: Module<DefiState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters,
  modules: {
    sushiswap,
    liquity
  }
};
