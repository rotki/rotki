import { taskManager } from '@/services/task-manager';
import { Blockchain } from '@/typing/types';

export interface Task<T extends TaskMeta> {
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
  DSR_HISTORY = 'dsr_history',
  MAKEDAO_VAULTS = 'makerdao_vaults',
  MAKERDAO_VAULT_DETAILS = 'makerdao_vault_details'
}

export function taskCompletion<R, M extends TaskMeta>(
  task: TaskType
): Promise<TaskResult<R, M>> {
  return new Promise((resolve, reject) => {
    taskManager.registerHandler<R, M>(task, (actionResult, meta) => {
      taskManager.unregisterHandler(task);
      const { result, message } = actionResult;
      if (message) {
        reject(new Error(message));
      } else {
        resolve({ result, meta });
      }
    });
  });
}

export interface TaskResult<R, M extends TaskMeta> {
  readonly result: R;
  readonly meta: M;
}
