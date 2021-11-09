import { AdexBalances, AdexHistory } from '@rotki/common/lib/staking/adex';
import { Eth2Deposit, Eth2Detail } from '@rotki/common/lib/staking/eth2';

export interface StakingState {
  readonly eth2Details: Eth2Detail[];
  readonly eth2Deposits: Eth2Deposit[];
  readonly adexBalances: AdexBalances;
  readonly adexHistory: AdexHistory;
}
