import { LiquityState } from '@/store/defi/liquity/types';

export const defaultState = (): LiquityState => ({
  balances: {},
  events: {},
  staking: {},
  stakingEvents: {}
});

export const state: LiquityState = defaultState();
