import { Module } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state, TaskState } from './state';

const namespaced: boolean = true;

export const tasks: Module<TaskState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
