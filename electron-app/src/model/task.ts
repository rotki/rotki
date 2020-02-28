import { Blockchain } from '@/typing/types';

export interface Task<T> {
  readonly id: number;
  readonly type: TaskType;
  readonly meta: T;
}

export interface TaskMeta {
  readonly description: string;
  readonly ignoreResult: boolean;
}

export interface ExchangeMeta extends TaskMeta {
  readonly name: string;
}

export interface BlockchainMetadata extends TaskMeta {
  readonly blockchain?: Blockchain;
}

export const createTask: <T extends TaskMeta>(
  id: number,
  type: TaskType,
  meta: T
) => Task<T> = (id, type, meta) => ({
  id,
  type,
  meta
});

export enum TaskType {
  ADD_ACCOUNT = 'add_account',
  REMOVE_ACCOUNT = 'remove_account',
  TRADE_HISTORY = 'process_trade_history',
  QUERY_BLOCKCHAIN_BALANCES = 'query_blockchain_balances_async',
  QUERY_EXCHANGE_BALANCES = 'query_exchange_balances_async',
  QUERY_BALANCES = 'query_balances_async',
  DSR_BALANCE = 'dsr_balance',
  DSR_HISTORY = 'dsr_history'
}
