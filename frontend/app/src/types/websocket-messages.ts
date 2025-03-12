import { CalendarEventPayload } from '@/types/history/calendar';
import { EvmChainAddress, EvmChainLikeAddress } from '@/types/history/events';
import { Blockchain, CommonQueryStatusData, type MaybePromise, type Notification } from '@rotki/common';
import { z } from 'zod';

export const MESSAGE_WARNING = 'warning';
const MESSAGE_ERROR = 'error';

const MessageVerbosity = z.enum([MESSAGE_WARNING, MESSAGE_ERROR]);

const LegacyMessageData = z.object({
  value: z.string(),
  verbosity: MessageVerbosity,
});

const BalanceSnapshotError = z.object({
  error: z.string(),
  location: z.string(),
});

export const EvmTransactionsQueryStatus = {
  ACCOUNT_CHANGE: 'account_change',
  QUERYING_EVM_TOKENS_TRANSACTIONS: 'querying_evm_tokens_transactions',
  QUERYING_INTERNAL_TRANSACTIONS: 'querying_internal_transactions',
  QUERYING_TRANSACTIONS: 'querying_transactions',
  QUERYING_TRANSACTIONS_FINISHED: 'querying_transactions_finished',
  QUERYING_TRANSACTIONS_STARTED: 'querying_transactions_started',
} as const;

export type EvmTransactionsQueryStatus = (typeof EvmTransactionsQueryStatus)[keyof typeof EvmTransactionsQueryStatus];

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

export const EvmTransactionQueryData = z
  .object({
    period: z.tuple([z.number(), z.number()]),
    status: z.nativeEnum(EvmTransactionsQueryStatus),
  })
  .merge(EvmChainAddress);

export const EvmUnDecodedTransactionsData = CommonQueryStatusData.extend({
  chain: z.string(),
});

export type EvmUnDecodedTransactionsData = z.infer<typeof EvmUnDecodedTransactionsData>;

export const EvmUnDecodedTransactionsDataWithSubtype = EvmUnDecodedTransactionsData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.EVM_UNDECODED_TRANSACTIONS),
});

export const EvmUndecodedTransactionBreakdown = z.object({
  total: z.number(),
  undecoded: z.number(),
});

export const EvmUndecodedTransactionResponse = z.record(EvmUndecodedTransactionBreakdown);

export type EvmUndecodedTransactionResponse = z.infer<typeof EvmUndecodedTransactionResponse>;

export const StatsPriceQueryData = CommonQueryStatusData.extend({
  counterparty: z.string(),
});

export type StatsPriceQueryData = z.infer<typeof StatsPriceQueryData>;

export const HistoryEventsQueryStatus = {
  QUERYING_EVENTS_FINISHED: 'querying_events_finished',
  QUERYING_EVENTS_STARTED: 'querying_events_started',
  QUERYING_EVENTS_STATUS_UPDATE: 'querying_events_status_update',
} as const;

export type HistoryEventsQueryStatus = (typeof HistoryEventsQueryStatus)[keyof typeof HistoryEventsQueryStatus];

export const HistoryEventsQueryData = z.object({
  eventType: z.string(),
  location: z.string(),
  name: z.string(),
  period: z.tuple([z.number(), z.number()]).optional(),
  status: z.nativeEnum(HistoryEventsQueryStatus),
});

export type HistoryEventsQueryData = z.infer<typeof HistoryEventsQueryData>;

export type BalanceSnapshotError = z.infer<typeof BalanceSnapshotError>;

export type EvmTransactionQueryData = z.infer<typeof EvmTransactionQueryData>;

export const PremiumStatusUpdateData = z.object({
  expired: z.boolean(),
  isPremiumActive: z.boolean(),
});

export type PremiumStatusUpdateData = z.infer<typeof PremiumStatusUpdateData>;

export const DbUpgradeStatusData = z.object({
  currentUpgrade: z.object({
    currentStep: z.number().nonnegative(),
    description: z.string().nullable(),
    totalSteps: z.number().nonnegative(),
    toVersion: z.number().nonnegative(),
  }),
  startVersion: z.number().nonnegative(),
  targetVersion: z.number().nonnegative(),
});

export type DbUpgradeStatusData = z.infer<typeof DbUpgradeStatusData>;

export const DbUploadResult = z.object({
  actionable: z.boolean(),
  message: z.string().nullable(),
  uploaded: z.boolean(),
});

export type DbUploadResult = z.infer<typeof DbUploadResult>;

export const DataMigrationStatusData = z.object({
  currentMigration: z.object({
    currentStep: z.number().nonnegative(),
    description: z.string().nullable(),
    totalSteps: z.number().nonnegative(),
    version: z.number().nonnegative(),
  }),
  startVersion: z.number().nonnegative(),
  targetVersion: z.number().nonnegative(),
});

export type DataMigrationStatusData = z.infer<typeof DataMigrationStatusData>;

export const MigratedAddresses = z.array(EvmChainLikeAddress);

export type MigratedAddresses = z.infer<typeof MigratedAddresses>;

export const NewDetectedToken = z.object({
  isIgnored: z.boolean().optional(),
  seenDescription: z.string().nullish(),
  seenTxHash: z.string().nullish(),
  tokenIdentifier: z.string(),
});

export type NewDetectedToken = z.infer<typeof NewDetectedToken>;

export const MissingApiKey = z.object({
  location: z.string(),
  service: z.string(),
});

export type MissingApiKey = z.infer<typeof MissingApiKey>;

export const RefreshBalancesType = {
  BLOCKCHAIN_BALANCES: 'blockchain_balances',
} as const;

export const RefreshBalancesData = z.object({
  blockchain: z.nativeEnum(Blockchain),
  type: z.nativeEnum(RefreshBalancesType),
});

export const AccountingRuleConflictData = z.object({
  numOfConflicts: z.number(),
});

export type AccountingRuleConflictData = z.infer<typeof AccountingRuleConflictData>;

export const ProtocolCacheUpdatesData = EvmUnDecodedTransactionsData.extend({
  protocol: z.string(),
});

export type ProtocolCacheUpdatesData = z.infer<typeof ProtocolCacheUpdatesData>;

export const ProtocolCacheUpdatesDataWithSubtype = ProtocolCacheUpdatesData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.PROTOCOL_CACHE_UPDATES),
});

export const HistoricalPriceQueryStatusDataWithSubtype = CommonQueryStatusData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.HISTORICAL_PRICE_QUERY_STATUS),
});

export const LiquityStakingQueryDataWithSubtype = CommonQueryStatusData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.LIQUITY_STAKING_QUERY),
});

export const StatsPriceQueryDataWithSubtype = StatsPriceQueryData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.STATS_PRICE_QUERY),
});

export const MultiplePricesQueryStatusWithSubtype = CommonQueryStatusData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.MULTIPLE_PRICES_QUERY_STATUS),
});

export const CsvImportResult = z.object({
  messages: z.array(z.object({
    isError: z.boolean(),
    msg: z.string(),
    rows: z.array(z.number()).optional(),
  })),
  processed: z.number(),
  sourceName: z.string(),
  total: z.number(),
});

export type CsvImportResult = z.infer<typeof CsvImportResult>;

export const CsvImportResultWithSubtype = CsvImportResult.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.CSV_IMPORT_RESULT),
});

export const ProgressUpdateResultData = z.discriminatedUnion('subtype', [
  EvmUnDecodedTransactionsDataWithSubtype,
  ProtocolCacheUpdatesDataWithSubtype,
  HistoricalPriceQueryStatusDataWithSubtype,
  CsvImportResultWithSubtype,
  LiquityStakingQueryDataWithSubtype,
  StatsPriceQueryDataWithSubtype,
  MultiplePricesQueryStatusWithSubtype,
]);

export type ProgressUpdateResultData = z.infer<typeof ProgressUpdateResultData>;

export const ExchangeUnknownAssetData = z.object({
  details: z.string(),
  identifier: z.string(),
  location: z.string(),
  name: z.string(),
});

export const GnosisPaySessionKeyExpiredData = z.object({
  error: z.string(),
});

export type GnosisPaySessionKeyExpiredData = z.infer<typeof GnosisPaySessionKeyExpiredData>;

export type ExchangeUnknownAssetData = z.infer<typeof ExchangeUnknownAssetData>;

export const SocketMessageType = {
  ACCOUNTING_RULE_CONFLICT: 'accounting_rule_conflict',
  BALANCES_SNAPSHOT_ERROR: 'balance_snapshot_error',
  CALENDAR_REMINDER: 'calendar_reminder',
  DATA_MIGRATION_STATUS: 'data_migration_status',
  DB_UPGRADE_STATUS: 'db_upgrade_status',
  DB_UPLOAD_RESULT: 'database_upload_result',
  EVM_ACCOUNTS_DETECTION: 'evmlike_accounts_detection',
  EVM_TRANSACTION_STATUS: 'evm_transaction_status',
  EXCHANGE_UNKNOWN_ASSET: 'exchange_unknown_asset',
  GNOSISPAY_SESSIONKEY_EXPIRED: 'gnosispay_sessionkey_expired',
  HISTORY_EVENTS_STATUS: 'history_events_status',
  LEGACY: 'legacy',
  MISSING_API_KEY: 'missing_api_key',
  NEW_EVM_TOKEN_DETECTED: 'new_evm_token_detected',
  PREMIUM_STATUS_UPDATE: 'premium_status_update',
  PROGRESS_UPDATES: 'progress_updates',
  REFRESH_BALANCES: 'refresh_balances',
} as const;

export type SocketMessageType = (typeof SocketMessageType)[keyof typeof SocketMessageType];

const UnknownWebsocketMessage = z.object({
  data: z.any(),
  type: z.string(),
});

const LegacyWebsocketMessage = z.object({
  data: LegacyMessageData,
  type: z.literal(SocketMessageType.LEGACY),
});

const BalancesSnapshotErrorMessage = z.object({
  data: BalanceSnapshotError,
  type: z.literal(SocketMessageType.BALANCES_SNAPSHOT_ERROR),
});

const EvmTransactionStatusMessage = z.object({
  data: EvmTransactionQueryData,
  type: z.literal(SocketMessageType.EVM_TRANSACTION_STATUS),
});

const HistoryEventsStatusMessage = z.object({
  data: HistoryEventsQueryData,
  type: z.literal(SocketMessageType.HISTORY_EVENTS_STATUS),
});

const PremiumStatusUpdateMessage = z.object({
  data: PremiumStatusUpdateData,
  type: z.literal(SocketMessageType.PREMIUM_STATUS_UPDATE),
});

const DbUpgradeStatusMessage = z.object({
  data: DbUpgradeStatusData,
  type: z.literal(SocketMessageType.DB_UPGRADE_STATUS),
});

const DbUploadResultMessage = z.object({
  data: DbUploadResult,
  type: z.literal(SocketMessageType.DB_UPLOAD_RESULT),
});

const DataMigrationStatusMessage = z.object({
  data: DataMigrationStatusData,
  type: z.literal(SocketMessageType.DATA_MIGRATION_STATUS),
});

const MigratedAccountsMessage = z.object({
  data: MigratedAddresses,
  type: z.literal(SocketMessageType.EVM_ACCOUNTS_DETECTION),
});

const NewEvmTokenDetectedMessage = z.object({
  data: NewDetectedToken,
  type: z.literal(SocketMessageType.NEW_EVM_TOKEN_DETECTED),
});

const MissingApiKeyMessage = z.object({
  data: MissingApiKey,
  type: z.literal(SocketMessageType.MISSING_API_KEY),
});

const RefreshBalancesMessage = z.object({
  data: RefreshBalancesData,
  type: z.literal(SocketMessageType.REFRESH_BALANCES),
});

const AccountingRuleConflictMessage = z.object({
  data: AccountingRuleConflictData,
  type: z.literal(SocketMessageType.ACCOUNTING_RULE_CONFLICT),
});

const CalendarReminderMessage = z.object({
  data: CalendarEventPayload,
  type: z.literal(SocketMessageType.CALENDAR_REMINDER),
});

const ExchangeUnknownAssetMessage = z.object({
  data: ExchangeUnknownAssetData,
  type: z.literal(SocketMessageType.EXCHANGE_UNKNOWN_ASSET),
});

const ProgressUpdatesMessage = z.object({
  data: ProgressUpdateResultData,
  type: z.literal(SocketMessageType.PROGRESS_UPDATES),
});

const GnosisPaySessionKeyExpiredMessage = z.object({
  data: GnosisPaySessionKeyExpiredData,
  type: z.literal(SocketMessageType.GNOSISPAY_SESSIONKEY_EXPIRED),
});

export const WebsocketMessage = z.union([
  UnknownWebsocketMessage,
  LegacyWebsocketMessage,
  BalancesSnapshotErrorMessage,
  EvmTransactionStatusMessage,
  HistoryEventsStatusMessage,
  PremiumStatusUpdateMessage,
  DbUpgradeStatusMessage,
  DataMigrationStatusMessage,
  MigratedAccountsMessage,
  NewEvmTokenDetectedMessage,
  MissingApiKeyMessage,
  RefreshBalancesMessage,
  DbUploadResultMessage,
  AccountingRuleConflictMessage,
  CalendarReminderMessage,
  ExchangeUnknownAssetMessage,
  ProgressUpdatesMessage,
  GnosisPaySessionKeyExpiredMessage,
]);

export type WebsocketMessage = z.infer<typeof WebsocketMessage>;

export interface CommonMessageHandler<T> {
  handle: (data: T) => MaybePromise<Notification>;
}
