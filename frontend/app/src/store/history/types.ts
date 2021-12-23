import { BigNumber } from '@rotki/common';
import { IgnoredActions } from '@/services/history/const';
import {
  AssetMovement,
  EntryMeta,
  EthTransaction,
  Trade,
  TradeLocation
} from '@/services/history/types';
import { FETCH_SOURCE } from '@/store/history/consts';
import { Nullable } from '@/types';
import { Collection } from '@/types/collection';
import { LedgerActionType } from '@/types/ledger-actions';
import { TaskMeta } from '@/types/task';

export type TradeEntry = Trade & EntryMeta;
export type AssetMovementEntry = AssetMovement & EntryMeta;
export type LedgerActionEntry = LedgerAction & EntryMeta;
export type EthTransactionEntry = EthTransaction & EntryMeta;

export interface HistoryState {
  ignored: IgnoredActions;
  associatedLocations: TradeLocation[];
  ledgerActions: Collection<LedgerActionEntry>;
  trades: Collection<TradeEntry>;
  assetMovements: Collection<AssetMovementEntry>;
  transactions: Collection<EthTransactionEntry>;
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
  TRADES = 'trade',
  MOVEMENTS = 'asset movement',
  ETH_TRANSACTIONS = 'ethereum transaction',
  LEDGER_ACTIONS = 'ledger action'
}

export type IgnoreActionPayload = {
  readonly actionIds: string[];
  readonly type: IgnoreActionType;
};

export type FetchSource = typeof FETCH_SOURCE[number];
