import { z } from 'zod';

export const MESSAGE_WARNING = 'warning';
const MESSAGE_ERROR = 'error';

const MessageVerbosity = z.enum([MESSAGE_WARNING, MESSAGE_ERROR]);

/** Why a backend user message happened: its family, one per cause. */
export const UserMessageKey = {
  AUTH: 'auth',
  BAD_DATA: 'bad_data',
  INTERNAL: 'internal',
  LOCAL_DB: 'local_db',
  NETWORK: 'network',
  PRICE: 'price',
  UNKNOWN_ASSET: 'unknown_asset',
  UNSUPPORTED: 'unsupported',
} as const;

export type UserMessageKey = (typeof UserMessageKey)[keyof typeof UserMessageKey];

const UserMessageBase = z.object({
  group: z.array(z.string().nullable()),
  subject: z.string().nullable(),
  value: z.string(),
  verbosity: MessageVerbosity,
});

/**
 * An `add_error` / `add_warning` from the backend.
 *
 * @remarks
 * Every emitter declares `key` (why it happened) and `fields` (the unrendered data its family
 * requires). `subject` (the location it happened to) is null for a message about no single
 * location. `value` is the rendered English sentence. `group` is the message's identity as the
 * backend's family declares it: messages with one `group` are one problem.
 *
 * The family fields are read as plain strings rather than as the backend's enums: they are only
 * compared for grouping, and an enum would drop the whole message the day the backend adds a
 * value. An unknown `key` still fails, since nothing could be said about its family.
 */
export const UserMessageData = z.discriminatedUnion('key', [
  UserMessageBase.extend({
    fields: z.object({ account: z.string().nullable(), service: z.string() }),
    key: z.literal(UserMessageKey.AUTH),
  }),
  UserMessageBase.extend({
    fields: z.object({ error: z.string(), record: z.string() }),
    key: z.literal(UserMessageKey.BAD_DATA),
  }),
  UserMessageBase.extend({
    fields: z.object({ operation: z.string() }),
    key: z.literal(UserMessageKey.INTERNAL),
  }),
  UserMessageBase.extend({
    fields: z.object({ entry: z.string() }),
    key: z.literal(UserMessageKey.LOCAL_DB),
  }),
  UserMessageBase.extend({
    fields: z.object({ error: z.string(), record: z.string() }),
    key: z.literal(UserMessageKey.NETWORK),
  }),
  UserMessageBase.extend({
    fields: z.object({ asset: z.string().nullable(), timestamp: z.number().nullable() }),
    key: z.literal(UserMessageKey.PRICE),
  }),
  UserMessageBase.extend({
    fields: z.object({ identifier: z.string() }),
    key: z.literal(UserMessageKey.UNKNOWN_ASSET),
  }),
  UserMessageBase.extend({
    fields: z.object({ feature: z.string() }),
    key: z.literal(UserMessageKey.UNSUPPORTED),
  }),
]);

export type UserMessageData = z.infer<typeof UserMessageData>;

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
  HISTORICAL_BALANCE_PROCESSING_COMPLETED: 'historical_balance_processing_completed',
  HISTORY_EVENTS_STATUS: 'history_events_status',
  INTERNAL_TX_FIXED: 'internal_tx_fixed',
  MISSING_API_KEY: 'missing_api_key',
  MONERIUM_SESSIONKEY_EXPIRED: 'monerium_sessionkey_expired',
  NEGATIVE_BALANCE_DETECTED: 'negative_balance_detected',
  NEW_TOKEN_DETECTED: 'new_token_detected',
  NO_AVAILABLE_INDEXERS: 'no_available_indexers',
  ORACLE_PENALIZED: 'oracle_penalized',
  PREMIUM_STATUS_UPDATE: 'premium_status_update',
  PROGRESS_UPDATES: 'progress_updates',
  REFRESH_BALANCES: 'refresh_balances',
  SOLANA_TOKENS_MIGRATION: 'solana_tokens_migration',
  TRANSACTION_STATUS: 'transaction_status',
  UNMATCHED_ASSET_MOVEMENTS: 'unmatched_asset_movements',
  UNMATCHED_BRIDGE_TRANSACTIONS: 'unmatched_bridge_transactions',
  USER_MESSAGE: 'user_message',
} as const;

export type SocketMessageType = (typeof SocketMessageType)[keyof typeof SocketMessageType];

export const SocketMessageProgressUpdateSubType = {
  CSV_IMPORT_RESULT: 'csv_import_result',
  HISTORICAL_BALANCE_PROCESSING: 'historical_balance_processing',
  HISTORICAL_PRICE_QUERY_STATUS: 'historical_price_query_status',
  LIQUITY_STAKING_QUERY: 'liquity_staking_query',
  MULTIPLE_PRICES_QUERY_STATUS: 'multiple_prices_query_status',
  PROTOCOL_CACHE_UPDATES: 'protocol_cache_updates',
  STATS_PRICE_QUERY: 'stats_price_query',
  UNDECODED_TRANSACTIONS: 'undecoded_transactions',
} as const;

export type SocketMessageProgressUpdateSubType = (typeof SocketMessageProgressUpdateSubType)[keyof typeof SocketMessageProgressUpdateSubType];
