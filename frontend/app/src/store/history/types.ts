import { LedgerAction } from '@/types/history/ledger-actions';
import { EntryMeta } from '@/types/history/meta';
import { AssetMovement } from '@/types/history/movements';
import { Trade } from '@/types/history/trades';
import {
  EthTransaction,
  EthTransactionEvent,
  TxEntryMeta
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
