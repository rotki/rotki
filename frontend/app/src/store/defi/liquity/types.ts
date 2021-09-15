import {
  LiquityAccountEvents,
  LiquityBalance,
  LiquityBalances,
  LiquityEvents
} from '@rotki/common/lib/liquity';
import { DefiProtocol } from '@/services/defi/consts';

export interface LiquitityState {
  readonly balances: LiquityBalances;
  readonly events: LiquityEvents;
}

export interface LiquityLoan {
  readonly owner: string;
  readonly protocol: DefiProtocol;
  readonly balances: LiquityBalance;
  readonly events: LiquityAccountEvents;
}
