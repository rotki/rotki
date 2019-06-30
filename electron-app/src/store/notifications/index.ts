import { mutations } from './mutations';
import { getters } from './getters';
import { actions } from './actions';
import { state, NotificationState } from './state';
import { Module } from 'vuex';
import { RotkehlchenState } from '@/store';

const namespaced: boolean = true;

export const notifications: Module<NotificationState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
