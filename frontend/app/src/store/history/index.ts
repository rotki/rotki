import { Module } from 'vuex';
import { HistoryState } from '@/store/history/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const history: Module<HistoryState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
