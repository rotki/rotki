import { Module } from 'vuex';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state, ReportState } from './state';

const namespaced: boolean = true;

export const reports: Module<ReportState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
