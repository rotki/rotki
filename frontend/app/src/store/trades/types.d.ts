import { TaskMeta } from '@/model/task';
import { Trade, TradeLocation } from '@/services/trades/types';
import { Status } from '@/store/const';

export interface TradesState {
  status: Status;
  limit: number;
  total: number;
  trades: Trade[];
}

export interface TradeMeta extends TaskMeta {
  readonly location: TradeLocation;
}
