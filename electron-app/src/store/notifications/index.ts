import { Module } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state, NotificationState } from './state';

const namespaced: boolean = true;

export const notifications: Module<NotificationState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
