import { Module } from 'vuex';
import { SettingsState } from '@/store/settings/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const settings: Module<SettingsState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
