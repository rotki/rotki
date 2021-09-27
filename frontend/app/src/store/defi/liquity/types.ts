import {
  LiquityBalance,
  LiquityBalances,
  TroveEvent,
  TroveEvents
} from '@rotki/common/lib/liquity';
import { DefiProtocol } from '@/services/defi/consts';

export interface LiquitityState {
  readonly balances: LiquityBalances;
  readonly events: TroveEvents;
}

export interface LiquityLoan {
  readonly owner: string;
  readonly protocol: DefiProtocol;
  readonly balance: LiquityBalance;
  readonly events: TroveEvent[];
}
