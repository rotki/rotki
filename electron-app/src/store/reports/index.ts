import { mutations } from './mutations';
import { getters } from './getters';
import { actions } from './actions';
import { state, TaxReportState } from './state';
import { Module } from 'vuex';
import { RotkehlchenState } from '@/store/store';

const namespaced: boolean = true;

export const reports: Module<TaxReportState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
