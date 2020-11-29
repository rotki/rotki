import { StakingState } from '@/store/staking/types';

export const defaultState = (): StakingState => ({
  eth2: {
    deposits: [],
    details: []
  }
});

export const state: StakingState = defaultState();
