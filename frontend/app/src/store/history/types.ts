import { IgnoredActions } from '@/services/history/const';
import {
  AssetMovement,
  EntryMeta,
  EthTransaction,
  LedgerAction,
  Trade,
  TradeLocation
} from '@/services/history/types';
import { Collection } from '@/types/collection';

export type TradeEntry = Trade & EntryMeta;
export type AssetMovementEntry = AssetMovement & EntryMeta;
export type LedgerActionEntry = LedgerAction & EntryMeta;
export type EthTransactionEntry = EthTransaction & EntryMeta;

export interface HistoryState {
  ignored: IgnoredActions;
  associatedLocations: TradeLocation[];
  trades: Collection<TradeEntry>;
  assetMovements: Collection<AssetMovementEntry>;
  transactions: Collection<EthTransactionEntry>;
  ledgerActions: Collection<LedgerActionEntry>;
}

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
