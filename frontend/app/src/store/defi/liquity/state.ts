import { LiquitityState } from '@/store/defi/liquity/types';

export const defaultState = (): LiquitityState => ({
  balances: {},
  events: {}
});

export const state: LiquitityState = defaultState();
