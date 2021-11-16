import { BigNumber } from '@rotki/common';
import { TaskMeta } from '@/model/task';
import { IgnoredActions } from '@/services/history/const';
import {
  AssetMovement,
  Trade,
  TradeLocation,
  Transactions
} from '@/services/history/types';
import { FETCH_SOURCE } from '@/store/history/consts';
import { Nullable } from '@/types';
import { LedgerActionType } from '@/types/ledger-actions';

export interface HistoricData<T> {
  readonly limit: number;
  readonly found: number;
  readonly data: T[];
}

type EntryMeta = { readonly ignoredInAccounting: boolean };

export type AssetMovementEntry = AssetMovement & EntryMeta;
export type TradeEntry = Trade & EntryMeta;
export type LedgerActionEntry = LedgerAction & EntryMeta;

export interface Trades extends HistoricData<TradeEntry> {}

export interface AssetMovements extends HistoricData<AssetMovementEntry> {}
export interface LedgerActions extends HistoricData<LedgerActionEntry> {}

export interface HistoryState {
  ignored: IgnoredActions;
  ledgerActions: LedgerActions;
  trades: Trades;
  assetMovements: AssetMovements;
  transactions: Transactions;
}

export interface LocationRequestMeta extends TaskMeta {
  readonly location: TradeLocation;
}
export interface LedgerAction {
  readonly identifier: number;
  readonly timestamp: number;
  readonly actionType: LedgerActionType;
  readonly location: TradeLocation;
  readonly amount: BigNumber;
  readonly asset: string;
  readonly rate?: Nullable<BigNumber>;
  readonly rateAsset?: Nullable<string>;
  readonly link?: Nullable<string>;
  readonly notes?: Nullable<string>;
}

export type UnsavedAction = Omit<LedgerAction, 'identifier'>;

export enum IgnoreActionType {
  MOVEMENTS = 'asset movement',
  TRADES = 'trade',
  LEDGER_ACTIONS = 'ledger action',
  ETH_TRANSACTIONS = 'ethereum transaction'
}
export type IgnoreActionPayload = {
  readonly actionIds: string[];
  readonly type: IgnoreActionType;
};

export type FetchSource = typeof FETCH_SOURCE[number];
