import { LedgerAction } from '@/types/history/ledger-actions';
import { EntryMeta } from '@/types/history/meta';
import { AssetMovement } from '@/types/history/movements';
import { Trade } from '@/types/history/trades';
import {
  EthTransaction,
  EthTransactionEvent,
  TxEntryMeta
} from '@/types/history/tx';

export type TradeEntry = Trade & EntryMeta;
export type AssetMovementEntry = AssetMovement & EntryMeta;
export type LedgerActionEntry = LedgerAction & EntryMeta;
export type EthTransactionEntry = EthTransaction & TxEntryMeta;
export type EthTransactionEventEntry = EthTransactionEvent & EntryMeta;

export enum IgnoreActionType {
  TRADES = 'trade',
  MOVEMENTS = 'asset_movement',
  ETH_TRANSACTIONS = 'ethereum_transaction',
  LEDGER_ACTIONS = 'ledger_action'
}

export type IgnoreActionPayload = {
  readonly actionIds: string[];
  readonly type: IgnoreActionType;
};
