import { DefiProtocol } from '@rotki/common/lib/blockchain';
import {
  LiquityBalance,
  LiquityBalances,
  LiquityStaking,
  LiquityStakingEvents,
  TroveEvent,
  TroveEvents
} from '@rotki/common/lib/liquity';

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
