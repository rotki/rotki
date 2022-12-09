import { type LedgerAction } from '@/types/history/ledger-actions';
import { type EntryMeta } from '@/types/history/meta';
import { type AssetMovement } from '@/types/history/movements';
import { type Trade } from '@/types/history/trades';
import {
  type EthTransaction,
  type EthTransactionEvent,
  type TxEntryMeta
} from '@/types/history/tx';

export interface TradeEntry extends Trade, EntryMeta {}
export interface AssetMovementEntry extends AssetMovement, EntryMeta {}
export interface LedgerActionEntry extends LedgerAction, EntryMeta {}
export interface EthTransactionEntry extends EthTransaction, TxEntryMeta {}
export interface EthTransactionEventEntry
  extends EthTransactionEvent,
    EntryMeta {}

export enum IgnoreActionType {
  TRADES = 'trade',
  MOVEMENTS = 'asset_movement',
  ETH_TRANSACTIONS = 'ethereum_transaction',
  LEDGER_ACTIONS = 'ledger_action'
}

export interface IgnoreActionPayload {
  readonly actionIds: string[];
  readonly type: IgnoreActionType;
}
