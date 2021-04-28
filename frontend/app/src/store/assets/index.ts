import { Module } from 'vuex';
import { AssetState } from '@/store/assets/types';
import { RotkehlchenState } from '@/store/types';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const assets: Module<AssetState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};
