import { Status } from '@/store/trades/status';
import { TradesState } from '@/store/trades/types';

export const defaultState = (): TradesState => ({
  status: Status.NONE,
  allTrades: [],
  externalTrades: []
});

export const state: TradesState = defaultState();
