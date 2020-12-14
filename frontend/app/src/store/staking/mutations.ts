import { Eth2Deposit, Eth2Detail, StakingState } from '@/store/staking/types';
import { defaultState } from '@/store/statistics/state';

type Mutations<S = StakingState> = {
  eth2Details(state: S, details: Eth2Detail[]): void;
  eth2Deposits(state: S, deposits: Eth2Deposit[]): void;
  reset(state: S): void;
};

export const mutations: Mutations = {
  eth2Details(state: StakingState, details: Eth2Detail[]) {
    state.eth2Details = details;
  },
  eth2Deposits(state: StakingState, details: Eth2Deposit[]) {
    state.eth2Deposits = details;
  },
  reset(state: StakingState) {
    Object.assign(state, defaultState());
  }
};
