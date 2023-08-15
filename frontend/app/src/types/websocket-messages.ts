import { z } from 'zod';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { EvmChainAddress } from '@/types/history/events';

export const MESSAGE_WARNING = 'warning';
const MESSAGE_ERROR = 'error';

const MessageVerbosity = z.enum([MESSAGE_WARNING, MESSAGE_ERROR]);

const LegacyMessageData = z.object({
  verbosity: MessageVerbosity,
  value: z.string()
});

const BalanceSnapshotError = z.object({
  location: z.string(),
  error: z.string()
});

export const EvmTransactionsQueryStatus = {
  ACCOUNT_CHANGE: 'account_change',
  QUERYING_TRANSACTIONS: 'querying_transactions',
  QUERYING_TRANSACTIONS_STARTED: 'querying_transactions_started',
  QUERYING_INTERNAL_TRANSACTIONS: 'querying_internal_transactions',
  QUERYING_EVM_TOKENS_TRANSACTIONS: 'querying_evm_tokens_transactions',
  QUERYING_TRANSACTIONS_FINISHED: 'querying_transactions_finished'
} as const;

export type EvmTransactionsQueryStatus =
  (typeof EvmTransactionsQueryStatus)[keyof typeof EvmTransactionsQueryStatus];

export const EvmTransactionQueryData = z
  .object({
    status: z.nativeEnum(EvmTransactionsQueryStatus),
    period: z.tuple([z.number(), z.number()])
  })
  .merge(EvmChainAddress);

export const HistoryEventsQueryStatus = {
  QUERYING_EVENTS_STARTED: 'querying_events_started',
  QUERYING_EVENTS_STATUS_UPDATE: 'querying_events_status_update',
  QUERYING_EVENTS_FINISHED: 'querying_events_finished'
} as const;

export type HistoryEventsQueryStatus =
  (typeof HistoryEventsQueryStatus)[keyof typeof HistoryEventsQueryStatus];

export const HistoryEventsQueryData = z.object({
  status: z.nativeEnum(HistoryEventsQueryStatus),
  period: z.tuple([z.number(), z.number()]).optional(),
  location: z.string(),
  name: z.string(),
  eventType: z.string()
});

export type HistoryEventsQueryData = z.infer<typeof HistoryEventsQueryData>;

export type BalanceSnapshotError = z.infer<typeof BalanceSnapshotError>;

export type EvmTransactionQueryData = z.infer<typeof EvmTransactionQueryData>;

export const PremiumStatusUpdateData = z.object({
  expired: z.boolean(),
  isPremiumActive: z.boolean()
});

export type PremiumStatusUpdateData = z.infer<typeof PremiumStatusUpdateData>;

export const DbUpgradeStatusData = z.object({
  startVersion: z.number().nonnegative(),
  targetVersion: z.number().nonnegative(),
  currentUpgrade: z.object({
    currentStep: z.number().nonnegative(),
    toVersion: z.number().nonnegative(),
    totalSteps: z.number().nonnegative()
  })
});

export type DbUpgradeStatusData = z.infer<typeof DbUpgradeStatusData>;

export const DataMigrationStatusData = z.object({
  startVersion: z.number().nonnegative(),
  targetVersion: z.number().nonnegative(),
  currentMigration: z.object({
    currentStep: z.number().nonnegative(),
    version: z.number().nonnegative(),
    totalSteps: z.number().nonnegative(),
    description: z.string().nullable()
  })
});

export type DataMigrationStatusData = z.infer<typeof DataMigrationStatusData>;

export const MigratedAddresses = z.array(EvmChainAddress);

export type MigratedAddresses = z.infer<typeof MigratedAddresses>;

export const NewDetectedToken = z.object({
  tokenIdentifier: z.string(),
  seenTxHash: z.string().nullish(),
  seenDescription: z.string().nullish(),
  isIgnored: z.boolean().optional()
});

export type NewDetectedToken = z.infer<typeof NewDetectedToken>;

export const MissingApiKey = z.object({
  location: z.string(),
  service: z.string()
});

export type MissingApiKey = z.infer<typeof MissingApiKey>;

export const RefreshBalancesType = {
  BLOCKCHAIN_BALANCES: 'blockchain_balances'
} as const;

export const RefreshBalancesData = z.object({
  type: z.nativeEnum(RefreshBalancesType),
  blockchain: z.nativeEnum(Blockchain)
});

export const SocketMessageType = {
  LEGACY: 'legacy',
  BALANCES_SNAPSHOT_ERROR: 'balance_snapshot_error',
  EVM_TRANSACTION_STATUS: 'evm_transaction_status',
  HISTORY_EVENTS_STATUS: 'history_events_status',
  PREMIUM_STATUS_UPDATE: 'premium_status_update',
  DB_UPGRADE_STATUS: 'db_upgrade_status',
  DATA_MIGRATION_STATUS: 'data_migration_status',
  EVM_ACCOUNTS_DETECTION: 'evm_accounts_detection',
  NEW_EVM_TOKEN_DETECTED: 'new_evm_token_detected',
  MISSING_API_KEY: 'missing_api_key',
  REFRESH_BALANCES: 'refresh_balances'
} as const;

export type SocketMessageType =
  (typeof SocketMessageType)[keyof typeof SocketMessageType];

const UnknownWebsocketMessage = z.object({
  type: z.string(),
  data: z.any()
});

const LegacyWebsocketMessage = z.object({
  type: z.literal(SocketMessageType.LEGACY),
  data: LegacyMessageData
});

const BalancesSnapshotErrorMessage = z.object({
  type: z.literal(SocketMessageType.BALANCES_SNAPSHOT_ERROR),
  data: BalanceSnapshotError
});

const EvmTransactionStatusMessage = z.object({
  type: z.literal(SocketMessageType.EVM_TRANSACTION_STATUS),
  data: EvmTransactionQueryData
});

const HistoryEventsStatusMessage = z.object({
  type: z.literal(SocketMessageType.HISTORY_EVENTS_STATUS),
  data: HistoryEventsQueryData
});

const PremiumStatusUpdateMessage = z.object({
  type: z.literal(SocketMessageType.PREMIUM_STATUS_UPDATE),
  data: PremiumStatusUpdateData
});

const DbUpgradeStatusMessage = z.object({
  type: z.literal(SocketMessageType.DB_UPGRADE_STATUS),
  data: DbUpgradeStatusData
});

const DataMigrationStatusMessage = z.object({
  type: z.literal(SocketMessageType.DATA_MIGRATION_STATUS),
  data: DataMigrationStatusData
});

const MigratedAccountsMessage = z.object({
  type: z.literal(SocketMessageType.EVM_ACCOUNTS_DETECTION),
  data: MigratedAddresses
});

const NewEvmTokenDetectedMessage = z.object({
  type: z.literal(SocketMessageType.NEW_EVM_TOKEN_DETECTED),
  data: NewDetectedToken
});

const MissingApiKeyMessage = z.object({
  type: z.literal(SocketMessageType.MISSING_API_KEY),
  data: MissingApiKey
});

const RefreshBalancesMessage = z.object({
  type: z.literal(SocketMessageType.REFRESH_BALANCES),
  data: RefreshBalancesData
});

export const WebsocketMessage = UnknownWebsocketMessage.or(
  LegacyWebsocketMessage
)
  .or(BalancesSnapshotErrorMessage)
  .or(EvmTransactionStatusMessage)
  .or(HistoryEventsStatusMessage)
  .or(PremiumStatusUpdateMessage)
  .or(DbUpgradeStatusMessage)
  .or(DataMigrationStatusMessage)
  .or(MigratedAccountsMessage)
  .or(NewEvmTokenDetectedMessage)
  .or(MissingApiKeyMessage)
  .or(RefreshBalancesMessage);

export type WebsocketMessage = z.infer<typeof WebsocketMessage>;
