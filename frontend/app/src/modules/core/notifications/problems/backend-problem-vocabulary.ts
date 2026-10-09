import { type MessageKey, msg } from '@/message-key';

/**
 * What a user message was reading or querying from a remote when it failed.
 *
 * @remarks
 * Mirrors the backend's `UserMessageRecord`. The wire schema reads the field as a plain string, so
 * a value a newer backend adds still arrives; it only lacks a label here.
 */
export const UserMessageRecord = {
  ASSET_MOVEMENT: 'asset_movement',
  ASSET_UPDATE: 'asset_update',
  BALANCE: 'balance',
  DATA_UPDATE: 'data_update',
  HISTORY_EVENT: 'history_event',
  MARKET: 'market',
  NODE: 'node',
  POSITION: 'position',
  PREMIUM_LIMITS: 'premium_limits',
  PROTOCOL_CACHE: 'protocol_cache',
  TRADE: 'trade',
  TRANSACTION: 'transaction',
  VALIDATOR: 'validator',
  WALLET: 'wallet',
} as const;

export type UserMessageRecord = (typeof UserMessageRecord)[keyof typeof UserMessageRecord];

/** What of rotki's own stored data was inconsistent, unreadable or unwritable: the backend's `UserMessageEntry`. */
export const UserMessageEntry = {
  ACCOUNTING_EVENT: 'accounting_event',
  ADDRESSBOOK_ENTRY: 'addressbook_entry',
  ASSET: 'asset',
  ASSET_UPDATE: 'asset_update',
  BALANCE_SNAPSHOT: 'balance_snapshot',
  BLOCKCHAIN_ACCOUNT: 'blockchain_account',
  DB_UPGRADE: 'db_upgrade',
  EXCHANGE_CREDENTIALS: 'exchange_credentials',
  HISTORY_EVENT: 'history_event',
  MANUALLY_TRACKED_BALANCE: 'manually_tracked_balance',
  MARGIN_POSITION: 'margin_position',
  MARKET: 'market',
  SETTING: 'setting',
  TAG: 'tag',
  TOKEN_LIST: 'token_list',
  TRANSACTION: 'transaction',
} as const;

export type UserMessageEntry = (typeof UserMessageEntry)[keyof typeof UserMessageEntry];

/** What rotki itself was doing when an invariant broke: the backend's `UserMessageOperation`. */
export const UserMessageOperation = {
  BACKGROUND_TASK: 'background_task',
  BALANCE_QUERY: 'balance_query',
  DATA_MIGRATION: 'data_migration',
  DECODER_INITIALIZATION: 'decoder_initialization',
  MODULE_ACTIVATION: 'module_activation',
  TRANSACTION_DECODING: 'transaction_decoding',
} as const;

export type UserMessageOperation = (typeof UserMessageOperation)[keyof typeof UserMessageOperation];

/** The kind of thing rotki does not support yet: the backend's `UserMessageFeature`. */
export const UserMessageFeature = {
  ASSET: 'asset',
  ASSET_UPDATE_SCHEMA: 'asset_update_schema',
  EXCHANGE_STRATEGY: 'exchange_strategy',
  MULTI_TRADE: 'multi_trade',
  VAULT_COLLATERAL_TYPE: 'vault_collateral_type',
} as const;

export type UserMessageFeature = (typeof UserMessageFeature)[keyof typeof UserMessageFeature];

export const RECORD_LABELS: Record<UserMessageRecord, MessageKey> = {
  [UserMessageRecord.ASSET_MOVEMENT]: msg.$t('backend_problems.record.asset_movement'),
  [UserMessageRecord.ASSET_UPDATE]: msg.$t('backend_problems.record.asset_update'),
  [UserMessageRecord.BALANCE]: msg.$t('backend_problems.record.balance'),
  [UserMessageRecord.DATA_UPDATE]: msg.$t('backend_problems.record.data_update'),
  [UserMessageRecord.HISTORY_EVENT]: msg.$t('backend_problems.record.history_event'),
  [UserMessageRecord.MARKET]: msg.$t('backend_problems.record.market'),
  [UserMessageRecord.NODE]: msg.$t('backend_problems.record.node'),
  [UserMessageRecord.POSITION]: msg.$t('backend_problems.record.position'),
  [UserMessageRecord.PREMIUM_LIMITS]: msg.$t('backend_problems.record.premium_limits'),
  [UserMessageRecord.PROTOCOL_CACHE]: msg.$t('backend_problems.record.protocol_cache'),
  [UserMessageRecord.TRADE]: msg.$t('backend_problems.record.trade'),
  [UserMessageRecord.TRANSACTION]: msg.$t('backend_problems.record.transaction'),
  [UserMessageRecord.VALIDATOR]: msg.$t('backend_problems.record.validator'),
  [UserMessageRecord.WALLET]: msg.$t('backend_problems.record.wallet'),
};

export const ENTRY_LABELS: Record<UserMessageEntry, MessageKey> = {
  [UserMessageEntry.ACCOUNTING_EVENT]: msg.$t('backend_problems.entry.accounting_event'),
  [UserMessageEntry.ADDRESSBOOK_ENTRY]: msg.$t('backend_problems.entry.addressbook_entry'),
  [UserMessageEntry.ASSET]: msg.$t('backend_problems.entry.asset'),
  [UserMessageEntry.ASSET_UPDATE]: msg.$t('backend_problems.entry.asset_update'),
  [UserMessageEntry.BALANCE_SNAPSHOT]: msg.$t('backend_problems.entry.balance_snapshot'),
  [UserMessageEntry.BLOCKCHAIN_ACCOUNT]: msg.$t('backend_problems.entry.blockchain_account'),
  [UserMessageEntry.DB_UPGRADE]: msg.$t('backend_problems.entry.db_upgrade'),
  [UserMessageEntry.EXCHANGE_CREDENTIALS]: msg.$t('backend_problems.entry.exchange_credentials'),
  [UserMessageEntry.HISTORY_EVENT]: msg.$t('backend_problems.entry.history_event'),
  [UserMessageEntry.MANUALLY_TRACKED_BALANCE]: msg.$t('backend_problems.entry.manually_tracked_balance'),
  [UserMessageEntry.MARGIN_POSITION]: msg.$t('backend_problems.entry.margin_position'),
  [UserMessageEntry.MARKET]: msg.$t('backend_problems.entry.market'),
  [UserMessageEntry.SETTING]: msg.$t('backend_problems.entry.setting'),
  [UserMessageEntry.TAG]: msg.$t('backend_problems.entry.tag'),
  [UserMessageEntry.TOKEN_LIST]: msg.$t('backend_problems.entry.token_list'),
  [UserMessageEntry.TRANSACTION]: msg.$t('backend_problems.entry.transaction'),
};

export const OPERATION_LABELS: Record<UserMessageOperation, MessageKey> = {
  [UserMessageOperation.BACKGROUND_TASK]: msg.$t('backend_problems.operation.background_task'),
  [UserMessageOperation.BALANCE_QUERY]: msg.$t('backend_problems.operation.balance_query'),
  [UserMessageOperation.DATA_MIGRATION]: msg.$t('backend_problems.operation.data_migration'),
  [UserMessageOperation.DECODER_INITIALIZATION]: msg.$t('backend_problems.operation.decoder_initialization'),
  [UserMessageOperation.MODULE_ACTIVATION]: msg.$t('backend_problems.operation.module_activation'),
  [UserMessageOperation.TRANSACTION_DECODING]: msg.$t('backend_problems.operation.transaction_decoding'),
};

export const FEATURE_LABELS: Record<UserMessageFeature, MessageKey> = {
  [UserMessageFeature.ASSET]: msg.$t('backend_problems.feature.asset'),
  [UserMessageFeature.ASSET_UPDATE_SCHEMA]: msg.$t('backend_problems.feature.asset_update_schema'),
  [UserMessageFeature.EXCHANGE_STRATEGY]: msg.$t('backend_problems.feature.exchange_strategy'),
  [UserMessageFeature.MULTI_TRADE]: msg.$t('backend_problems.feature.multi_trade'),
  [UserMessageFeature.VAULT_COLLATERAL_TYPE]: msg.$t('backend_problems.feature.vault_collateral_type'),
};

/**
 * The label key for a vocabulary value, or undefined for a value this frontend does not know.
 *
 * @remarks
 * A newer backend can send a value added after this build, so the lookup is by string; the caller
 * falls back to the backend's own sentence.
 */
export function labelOf(labels: Record<string, MessageKey>, value: string): MessageKey | undefined {
  return new Map<string, MessageKey>(Object.entries(labels)).get(value);
}
