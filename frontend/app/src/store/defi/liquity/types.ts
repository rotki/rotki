import {
  LiquityBalance,
  LiquityBalances,
  LiquityStaking,
  LiquityStakingEvents,
  TroveEvent,
  TroveEvents
} from '@rotki/common/lib/liquity';
import { DefiProtocol } from '@/services/defi/consts';

export interface LiquityState {
  readonly balances: LiquityBalances;
  readonly events: TroveEvents;
  readonly staking: LiquityStaking;
  readonly stakingEvents: LiquityStakingEvents;
}

export interface LiquityLoan {
  readonly owner: string;
  readonly protocol: DefiProtocol;
  readonly balance: LiquityBalance;
  readonly events: TroveEvent[];
}
