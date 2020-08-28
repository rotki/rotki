import { TaskMeta } from '@/model/task';
import { AssetMovement } from '@/services/balances/types';
import { Trade, TradeLocation } from '@/services/history/types';

export interface HistoricData<T> {
  readonly limit: number;
  readonly found: number;
  readonly data: T[];
}

export interface Trades extends HistoricData<Trade> {}

export interface AssetMovements extends HistoricData<AssetMovement> {}

export interface HistoryState {
  trades: Trades;
  assetMovements: AssetMovements;
}

export interface LocationRequestMeta extends TaskMeta {
  readonly location: TradeLocation;
}
