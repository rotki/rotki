import { default as BigNumber } from 'bignumber.js';
import { TaskMeta } from '@/model/task';
import {
  AssetMovement,
  EthTransaction,
  Trade,
  TradeLocation
} from '@/services/history/types';
import {
  IGNORE_ACTION_TYPE,
  LEDGER_ACTION_TYPES
} from '@/store/history/consts';

export interface HistoricData<T> {
  readonly limit: number;
  readonly found: number;
  readonly data: T[];
}

interface Trades extends HistoricData<Trade> {}

interface AssetMovements extends HistoricData<AssetMovement> {}

interface EthTransactions extends HistoricData<EthTransaction> {}

interface LedgerActions extends HistoricData<LedgerAction> {}

export interface HistoryState {
  ledgerActions: LedgerActions;
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

export type LedgerActionType = typeof LEDGER_ACTION_TYPES[number];

export interface LedgerAction {
  readonly identifier: number;
  readonly timestamp: number;
  readonly actionType: LedgerActionType;
  readonly location: TradeLocation;
  readonly amount: BigNumber;
  readonly asset: string;
  readonly link: string;
  readonly notes: string;
}

export type UnsavedAction = Omit<LedgerAction, 'identifier'>;

export type ActionType = typeof IGNORE_ACTION_TYPE[number];
export type IgnoreActionPayload = {
  readonly actionIds: string[];
  readonly type: ActionType;
};
