import { StakingState } from '@/store/staking/types';

export const defaultState = (): StakingState => ({
  eth2: {
    deposits: [],
    totals: {}
  }
});

export const state: StakingState = defaultState();
