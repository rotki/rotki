import { Module } from 'vuex';
import { StatisticsState } from '@/store/statistics/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const statistics: Module<StatisticsState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
