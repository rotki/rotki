import { Module } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { SessionState, state } from './state';

const namespaced: boolean = true;

export const session: Module<SessionState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
