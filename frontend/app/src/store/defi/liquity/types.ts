import { LiquityBalances, LiquityEvents } from '@rotki/common/lib/liquity';

export interface LiquitityState {
  readonly balances: LiquityBalances;
  readonly events: LiquityEvents;
}
