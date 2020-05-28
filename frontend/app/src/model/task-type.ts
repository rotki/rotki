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
