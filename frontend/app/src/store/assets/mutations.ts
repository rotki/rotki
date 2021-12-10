import { MutationTree } from 'vuex';
import { AssetState } from '@/store/assets/types';

export const mutations: MutationTree<AssetState> = {
  reset(state: AssetState) {
    Object.assign(state, {});
  }
};
