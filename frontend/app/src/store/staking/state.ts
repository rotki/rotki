import { StakingState } from '@/store/staking/types';
import { Zero } from '@/utils/bignumbers';

export const defaultState = (): StakingState => ({
  eth2Deposits: [],
  eth2Details: [],
  eth2DailyStats: {
    entries: [],
    entriesFound: 0,
    entriesTotal: 0,
    sumPnl: Zero,
    sumUsdValue: Zero
  },
  adexBalances: {},
  adexHistory: {}
});

export const state: StakingState = defaultState();
