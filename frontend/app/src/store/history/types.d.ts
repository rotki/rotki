import { default as BigNumber } from 'bignumber.js';
import { TaskMeta } from '@/model/task';
import {
  AssetMovement,
  EthTransaction,
  Trade,
  TradeLocation
} from '@/services/history/types';

export interface HistoricData<T> {
  readonly limit: number;
  readonly found: number;
  readonly data: T[];
}

export interface Trades extends HistoricData<Trade> {}

export interface AssetMovements extends HistoricData<AssetMovement> {}

export interface EthTransactions extends HistoricData<EthTransaction> {}

export interface HistoryState {
  trades: Trades;
  assetMovements: AssetMovements;
  transactions: EthTransactions;
}

export interface LocationRequestMeta extends TaskMeta {
  readonly location: TradeLocation;
}

export interface AccountRequestMeta extends TaskMeta {
  readonly address: string;
}

export type EthTransactionWithFee = EthTransaction & {
  readonly gasFee: BigNumber;
  readonly key: string;
};
