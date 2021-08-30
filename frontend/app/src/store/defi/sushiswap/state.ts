import { SushiswapState } from '@/store/defi/sushiswap/types';

export const defaultState = (): SushiswapState => ({
  balances: {},
  trades: {},
  events: {}
});

export const state: SushiswapState = defaultState();
