import { Status } from '@/store/const';
import { TradesState } from '@/store/trades/types';

export const defaultState = (): TradesState => ({
  status: Status.NONE,
  trades: [],
  limit: -1,
  total: 0
});

export const state: TradesState = defaultState();
