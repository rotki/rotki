import { z } from 'zod';
import { Blockchain, type Notification } from '@rotki/common';
import { EvmChainAddress, EvmChainLikeAddress } from '@/types/history/events';
import { CalendarEventPayload } from '@/types/history/calendar';

export const MESSAGE_WARNING = 'warning';
const MESSAGE_ERROR = 'error';

const MessageVerbosity = z.enum([MESSAGE_WARNING, MESSAGE_ERROR]);

const LegacyMessageData = z.object({
  verbosity: MessageVerbosity,
  value: z.string(),
});

const BalanceSnapshotError = z.object({
  location: z.string(),
  error: z.string(),
});

export const EvmTransactionsQueryStatus = {
  ACCOUNT_CHANGE: 'account_change',
  QUERYING_TRANSACTIONS: 'querying_transactions',
  QUERYING_TRANSACTIONS_STARTED: 'querying_transactions_started',
  QUERYING_INTERNAL_TRANSACTIONS: 'querying_internal_transactions',
  QUERYING_EVM_TOKENS_TRANSACTIONS: 'querying_evm_tokens_transactions',
  QUERYING_TRANSACTIONS_FINISHED: 'querying_transactions_finished',
} as const;

export type EvmTransactionsQueryStatus = (typeof EvmTransactionsQueryStatus)[keyof typeof EvmTransactionsQueryStatus];

export const EvmTransactionQueryData = z
  .object({
    status: z.nativeEnum(EvmTransactionsQueryStatus),
    period: z.tuple([z.number(), z.number()]),
  })
  .merge(EvmChainAddress);

export const EvmUnDecodedTransactionsData = z.object({
  chain: z.string(),
  processed: z.number(),
  total: z.number(),
});

export type EvmUnDecodedTransactionsData = z.infer<typeof EvmUnDecodedTransactionsData>;

export const EvmUndecodedTransactionBreakdown = z.object({
  total: z.number(),
  undecoded: z.number(),
});

export const EvmUndecodedTransactionResponse = z.record(EvmUndecodedTransactionBreakdown);

export type EvmUndecodedTransactionResponse = z.infer<typeof EvmUndecodedTransactionResponse>;

export const HistoryEventsQueryStatus = {
  QUERYING_EVENTS_STARTED: 'querying_events_started',
  QUERYING_EVENTS_STATUS_UPDATE: 'querying_events_status_update',
  QUERYING_EVENTS_FINISHED: 'querying_events_finished',
} as const;

export type HistoryEventsQueryStatus = (typeof HistoryEventsQueryStatus)[keyof typeof HistoryEventsQueryStatus];

export const HistoryEventsQueryData = z.object({
  status: z.nativeEnum(HistoryEventsQueryStatus),
  period: z.tuple([z.number(), z.number()]).optional(),
  location: z.string(),
  name: z.string(),
  eventType: z.string(),
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
  startVersion: z.number().nonnegative(),
  targetVersion: z.number().nonnegative(),
  currentUpgrade: z.object({
    currentStep: z.number().nonnegative(),
    toVersion: z.number().nonnegative(),
    totalSteps: z.number().nonnegative(),
  }),
});

export type DbUpgradeStatusData = z.infer<typeof DbUpgradeStatusData>;

export const DbUploadResult = z.object({
  uploaded: z.boolean(),
  actionable: z.boolean(),
  message: z.string().nullable(),
});

export type DbUploadResult = z.infer<typeof DbUploadResult>;

export const DataMigrationStatusData = z.object({
  startVersion: z.number().nonnegative(),
  targetVersion: z.number().nonnegative(),
  currentMigration: z.object({
    currentStep: z.number().nonnegative(),
    version: z.number().nonnegative(),
    totalSteps: z.number().nonnegative(),
    description: z.string().nullable(),
  }),
});

export type DataMigrationStatusData = z.infer<typeof DataMigrationStatusData>;

export const MigratedAddresses = z.array(EvmChainLikeAddress);

export type MigratedAddresses = z.infer<typeof MigratedAddresses>;

export const NewDetectedToken = z.object({
  tokenIdentifier: z.string(),
  seenTxHash: z.string().nullish(),
  seenDescription: z.string().nullish(),
  isIgnored: z.boolean().optional(),
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
  type: z.nativeEnum(RefreshBalancesType),
  blockchain: z.nativeEnum(Blockchain),
});

export const AccountingRuleConflictData = z.object({
  numOfConflicts: z.number(),
});

export type AccountingRuleConflictData = z.infer<typeof AccountingRuleConflictData>;

export const ProtocolCacheUpdatesData = EvmUnDecodedTransactionsData.extend({
  protocol: z.string(),
});

export type ProtocolCacheUpdatesData = z.infer<typeof ProtocolCacheUpdatesData>;

export const CsvImportResult = z.object({
  sourceName: z.string(),
  totalEntries: z.number(),
  importedEntries: z.number(),
  messages: z.array(z.object({
    isError: z.boolean(),
    msg: z.string(),
    rows: z.array(z.number()).optional(),
  })),
});

export type CsvImportResult = z.infer<typeof CsvImportResult>;

export const ExchangeUnknownAssetData = z.object({
  details: z.string(),
  identifier: z.string(),
  location: z.string(),
  name: z.string(),
});

export type ExchangeUnknownAssetData = z.infer<typeof ExchangeUnknownAssetData>;

export const SocketMessageType = {
  LEGACY: 'legacy',
  BALANCES_SNAPSHOT_ERROR: 'balance_snapshot_error',
  EVM_TRANSACTION_STATUS: 'evm_transaction_status',
  EVM_UNDECODED_TRANSACTIONS: 'evm_undecoded_transactions',
  HISTORY_EVENTS_STATUS: 'history_events_status',
  PREMIUM_STATUS_UPDATE: 'premium_status_update',
  DB_UPGRADE_STATUS: 'db_upgrade_status',
  DATA_MIGRATION_STATUS: 'data_migration_status',
  EVM_ACCOUNTS_DETECTION: 'evmlike_accounts_detection',
  NEW_EVM_TOKEN_DETECTED: 'new_evm_token_detected',
  MISSING_API_KEY: 'missing_api_key',
  REFRESH_BALANCES: 'refresh_balances',
  DB_UPLOAD_RESULT: 'database_upload_result',
  ACCOUNTING_RULE_CONFLICT: 'accounting_rule_conflict',
  CALENDAR_REMINDER: 'calendar_reminder',
  PROTOCOL_CACHE_UPDATES: 'protocol_cache_updates',
  CSV_IMPORT_RESULT: 'csv_import_result',
  EXCHANGE_UNKNOWN_ASSET: 'exchange_unknown_asset',
} as const;

export type SocketMessageType = (typeof SocketMessageType)[keyof typeof SocketMessageType];

const UnknownWebsocketMessage = z.object({
  type: z.string(),
  data: z.any(),
});

const LegacyWebsocketMessage = z.object({
  type: z.literal(SocketMessageType.LEGACY),
  data: LegacyMessageData,
});

const BalancesSnapshotErrorMessage = z.object({
  type: z.literal(SocketMessageType.BALANCES_SNAPSHOT_ERROR),
  data: BalanceSnapshotError,
});

const EvmTransactionStatusMessage = z.object({
  type: z.literal(SocketMessageType.EVM_TRANSACTION_STATUS),
  data: EvmTransactionQueryData,
});

const HistoryEventsStatusMessage = z.object({
  type: z.literal(SocketMessageType.HISTORY_EVENTS_STATUS),
  data: HistoryEventsQueryData,
});

const PremiumStatusUpdateMessage = z.object({
  type: z.literal(SocketMessageType.PREMIUM_STATUS_UPDATE),
  data: PremiumStatusUpdateData,
});

const DbUpgradeStatusMessage = z.object({
  type: z.literal(SocketMessageType.DB_UPGRADE_STATUS),
  data: DbUpgradeStatusData,
});

const DbUploadResultMessage = z.object({
  type: z.literal(SocketMessageType.DB_UPLOAD_RESULT),
  data: DbUploadResult,
});

const DataMigrationStatusMessage = z.object({
  type: z.literal(SocketMessageType.DATA_MIGRATION_STATUS),
  data: DataMigrationStatusData,
});

const MigratedAccountsMessage = z.object({
  type: z.literal(SocketMessageType.EVM_ACCOUNTS_DETECTION),
  data: MigratedAddresses,
});

const NewEvmTokenDetectedMessage = z.object({
  type: z.literal(SocketMessageType.NEW_EVM_TOKEN_DETECTED),
  data: NewDetectedToken,
});

const MissingApiKeyMessage = z.object({
  type: z.literal(SocketMessageType.MISSING_API_KEY),
  data: MissingApiKey,
});

const RefreshBalancesMessage = z.object({
  type: z.literal(SocketMessageType.REFRESH_BALANCES),
  data: RefreshBalancesData,
});

const AccountingRuleConflictMessage = z.object({
  type: z.literal(SocketMessageType.ACCOUNTING_RULE_CONFLICT),
  data: AccountingRuleConflictData,
});

const CalendarReminderMessage = z.object({
  type: z.literal(SocketMessageType.CALENDAR_REMINDER),
  data: CalendarEventPayload,
});

const ProtocolCacheUpdatesMessage = z.object({
  type: z.literal(SocketMessageType.PROTOCOL_CACHE_UPDATES),
  data: ProtocolCacheUpdatesData,
});

const CsvImportResultMessage = z.object({
  type: z.literal(SocketMessageType.CSV_IMPORT_RESULT),
  data: CsvImportResult,
});

const ExchangeUnknownAssetMessage = z.object({
  type: z.literal(SocketMessageType.EXCHANGE_UNKNOWN_ASSET),
  data: ExchangeUnknownAssetData,
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
  ProtocolCacheUpdatesMessage,
  CsvImportResultMessage,
  ExchangeUnknownAssetMessage,
]);

export type WebsocketMessage = z.infer<typeof WebsocketMessage>;

export interface CommonMessageHandler<T> {
  handle: (data: T) => Notification;
}
