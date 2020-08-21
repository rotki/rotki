import { Status } from '@/store/const';
import { TradesState } from '@/store/trades/types';

export const defaultState = (): TradesState => ({
  status: Status.NONE,
  trades: []
});

export const state: TradesState = defaultState();
