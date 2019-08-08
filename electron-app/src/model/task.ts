export interface Task {
  readonly id: number;
  readonly type: TaskType;
  readonly description: string;
  readonly asyncResult: boolean;
}

export const createTask: (
  id: number,
  type: TaskType,
  description: string,
  asyncResult: boolean
) => Task = (id, type, description, asyncResult) => ({
  id,
  type,
  description,
  asyncResult
});

export enum TaskType {
  TRADE_HISTORY = 'process_trade_history',
  QUERY_BLOCKCHAIN_BALANCES = 'query_blockchain_balances_async',
  QUERY_EXCHANGE_BALANCES = 'query_exchange_balances_async',
  USER_SETTINGS_QUERY_BLOCKCHAIN_BALANCES = 'user_settings_query_blockchain_balances',
  QUERY_BALANCES = 'query_balances_async'
}
