import { TaskMeta } from '@/model/task';
import { Trade, TradeLocation } from '@/services/trades/types';

export interface TradesState {
  limit: number;
  total: number;
  trades: Trade[];
}

export interface LocationRequestMeta extends TaskMeta {
  readonly location: TradeLocation;
}
