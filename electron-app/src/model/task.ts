export default class Task {
  constructor(
    readonly id: number,
    readonly type: string,
    readonly should_expect_callback: boolean
  ) {}
}

export enum TaskType {
  TRADE_HISTORY = 'process_trade_history',
  QUERY_BLOCKCHAIN_BALANCES = 'query_blockchain_balances_async',
  QUERY_EXCHANGE_BALANCES = 'query_exchange_balances_async',
  USER_SETTINGS_QUERY_BLOCKCHAIN_BALANCES = 'user_settings_query_blockchain_balances',
  QUERY_BALANCES = 'query_balances_async'
}
