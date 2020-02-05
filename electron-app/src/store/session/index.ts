import { actions } from './actions';
import { mutations } from './mutations';
import { getters } from './getters';
import { SessionState, state } from './state';
import { Module } from 'vuex';
import { RotkehlchenState } from '@/store/store';

const namespaced: boolean = true;

export const session: Module<SessionState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
