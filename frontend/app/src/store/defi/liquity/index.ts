import { Module } from 'vuex';
import { LiquityState } from '@/store/defi/liquity/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const liquity: Module<LiquityState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
