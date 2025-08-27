import { z } from 'zod/v4';

export const MESSAGE_WARNING = 'warning';
const MESSAGE_ERROR = 'error';

export const MessageVerbosity = z.enum([MESSAGE_WARNING, MESSAGE_ERROR]);

export const LegacyMessageData = z.object({
  value: z.string(),
  verbosity: MessageVerbosity,
});

export type LegacyMessageData = z.infer<typeof LegacyMessageData>;

export const SocketMessageType = {
  ACCOUNTING_RULE_CONFLICT: 'accounting_rule_conflict',
  BALANCES_SNAPSHOT_ERROR: 'balance_snapshot_error',
  BINANCE_PAIRS_MISSING: 'binance_pairs_missing',
  CALENDAR_REMINDER: 'calendar_reminder',
  DATA_MIGRATION_STATUS: 'data_migration_status',
  DATABASE_UPLOAD_PROGRESS: 'database_upload_progress',
  DB_UPGRADE_STATUS: 'db_upgrade_status',
  DB_UPLOAD_RESULT: 'database_upload_result',
  EVM_ACCOUNTS_DETECTION: 'evmlike_accounts_detection',
  EXCHANGE_UNKNOWN_ASSET: 'exchange_unknown_asset',
  GNOSISPAY_SESSIONKEY_EXPIRED: 'gnosispay_sessionkey_expired',
  HISTORY_EVENTS_STATUS: 'history_events_status',
  LEGACY: 'legacy',
  MISSING_API_KEY: 'missing_api_key',
  NEW_EVM_TOKEN_DETECTED: 'new_evm_token_detected',
  PREMIUM_STATUS_UPDATE: 'premium_status_update',
  PROGRESS_UPDATES: 'progress_updates',
  REFRESH_BALANCES: 'refresh_balances',
  SOLANA_TOKENS_MIGRATION: 'solana_tokens_migration',
  TRANSACTION_STATUS: 'transaction_status',
} as const;

export type SocketMessageType = (typeof SocketMessageType)[keyof typeof SocketMessageType];

export function isSocketMessageType(type: string): type is SocketMessageType {
  return Object.values(SocketMessageType).includes(type as SocketMessageType);
}

export const SocketMessageProgressUpdateSubType = {
  CSV_IMPORT_RESULT: 'csv_import_result',
  EVM_UNDECODED_TRANSACTIONS: 'evm_undecoded_transactions',
  HISTORICAL_PRICE_QUERY_STATUS: 'historical_price_query_status',
  LIQUITY_STAKING_QUERY: 'liquity_staking_query',
  MULTIPLE_PRICES_QUERY_STATUS: 'multiple_prices_query_status',
  PROTOCOL_CACHE_UPDATES: 'protocol_cache_updates',
  STATS_PRICE_QUERY: 'stats_price_query',
} as const;

export type SocketMessageProgressUpdateSubType = (typeof SocketMessageProgressUpdateSubType)[keyof typeof SocketMessageProgressUpdateSubType];
