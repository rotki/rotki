import { Status } from '@/store/const';
import { TradesState } from '@/store/trades/types';

export const defaultState = (): TradesState => ({
  status: Status.NONE,
  trades: [],
  limit: -1
});

export const state: TradesState = defaultState();
