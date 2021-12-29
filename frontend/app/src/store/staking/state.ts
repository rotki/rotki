import { StakingState } from '@/store/staking/types';

export const defaultState = (): StakingState => ({
  eth2Deposits: [],
  eth2Details: [],
  eth2DailyStats: {
    entries: [],
    entriesFound: 0,
    entriesTotal: 0
  },
  adexBalances: {},
  adexHistory: {}
});

export const state: StakingState = defaultState();
