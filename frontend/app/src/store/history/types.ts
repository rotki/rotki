import {
  AssetMovement,
  EntryMeta,
  EthTransaction,
  EthTransactionEvent,
  LedgerAction,
  Trade
} from '@/services/history/types';

export type TradeEntry = Trade & EntryMeta;
export type AssetMovementEntry = AssetMovement & EntryMeta;
export type LedgerActionEntry = LedgerAction & EntryMeta;
export type EthTransactionEntry = EthTransaction & EntryMeta;
export type EthTransactionEventEntry = EthTransactionEvent & EntryMeta;

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
