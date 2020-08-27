import { TradesState } from '@/store/trades/types';

export const defaultState = (): TradesState => ({
  trades: [],
  limit: -1,
  total: 0
});

export const state: TradesState = defaultState();
