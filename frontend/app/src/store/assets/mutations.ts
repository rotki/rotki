import { MutationTree } from 'vuex';
import { AssetState } from '@/store/assets/types';
import { defaultState } from '@/store/notifications/state';

export const mutations: MutationTree<AssetState> = {
  reset(state: AssetState) {
    Object.assign(state, defaultState());
  }
};
