import { AdexBalances, AdexHistory } from '@rotki/common/lib/staking/adex';

export interface StakingState {
  readonly adexBalances: AdexBalances;
  readonly adexHistory: AdexHistory;
}
