import { StakingState } from '@/store/staking/types';

export const defaultState = (): StakingState => ({
  adexBalances: {},
  adexHistory: {}
});

export const state: StakingState = defaultState();
