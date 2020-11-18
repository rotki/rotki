import { Eth2Staking, StakingState } from '@/store/staking/types';
import { defaultState } from '@/store/statistics/state';

type Mutations<S = StakingState> = {
  eth2(state: S, eth2Staking: Eth2Staking): void;
  reset(state: S): void;
};

export const mutations: Mutations = {
  eth2(state: StakingState, eth2Staking: Eth2Staking) {
    state.eth2 = eth2Staking;
  },
  reset(state: StakingState) {
    Object.assign(state, defaultState());
  }
};
