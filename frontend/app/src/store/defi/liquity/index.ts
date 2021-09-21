import { Module } from 'vuex';
import { LiquitityState } from '@/store/defi/liquity/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const liquity: Module<LiquitityState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
