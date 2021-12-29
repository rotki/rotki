import { AdexBalances, AdexHistory } from '@rotki/common/lib/staking/adex';
import {
  Eth2DailyStats,
  Eth2Deposits,
  Eth2Details
} from '@rotki/common/lib/staking/eth2';

export interface StakingState {
  readonly eth2Details: Eth2Details;
  readonly eth2Deposits: Eth2Deposits;
  readonly eth2DailyStats: Eth2DailyStats;
  readonly adexBalances: AdexBalances;
  readonly adexHistory: AdexHistory;
}
