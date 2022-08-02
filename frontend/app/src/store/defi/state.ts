import { DefiState } from '@/store/defi/types';

export const defaultState = (): DefiState => ({
  allProtocols: {},
  airdrops: {}
});

export const state: DefiState = defaultState();
