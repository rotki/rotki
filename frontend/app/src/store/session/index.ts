import { Module } from 'vuex';
import { SessionState } from '@/store/session/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const session: Module<SessionState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
