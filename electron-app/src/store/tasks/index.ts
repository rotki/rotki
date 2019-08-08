import { mutations } from './mutations';
import { getters } from './getters';
import { actions } from './actions';
import { state, TaskState } from './state';
import { Module } from 'vuex';
import { RotkehlchenState } from '@/store';

const namespaced: boolean = true;

export const tasks: Module<TaskState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
