import { MutationTree } from 'vuex';
import { defaultState } from '@/store/defi/state';
import { Airdrops, AllDefiProtocols, DefiState } from '@/store/defi/types';

export const mutations: MutationTree<DefiState> = {
  allDefiProtocols(state: DefiState, allProtocols: AllDefiProtocols) {
    state.allProtocols = allProtocols;
  },
  airdrops(state: DefiState, airdrops: Airdrops) {
    state.airdrops = airdrops;
  },
  reset(state: DefiState) {
    Object.assign(state, defaultState());
  }
};
