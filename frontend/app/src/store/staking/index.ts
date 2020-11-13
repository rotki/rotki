import { Module } from 'vuex';
import { StakingState } from '@/store/staking/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const staking: Module<StakingState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
