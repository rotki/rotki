import type { Notification } from '@rotki/common';
import { z } from 'zod/v4';
import { CalendarEventWithReminder } from '@/types/history/calendar';
import { LegacyMessageData, SocketMessageType } from './types/base';
import {
  AccountingRuleConflictData,
  ExchangeUnknownAssetData,
  NewDetectedToken,
  RefreshBalancesData,
} from './types/business-types';
import {
  BalanceSnapshotError,
  BinancePairsMissingData,
  GnosisPaySessionKeyExpiredData,
  MissingApiKey,
  SolanaTokensMigrationData,
} from './types/notification-types';
import { DatabaseUploadProgress, DbUploadResult, PremiumStatusUpdateData } from './types/shared-types';
import {
  DataMigrationStatusData,
  DbUpgradeStatusData,
  HistoryEventsQueryData,
  MigratedAddresses,
  ProgressUpdateResultData,
  UnifiedTransactionStatusData,
} from './types/status-types';

const LegacyWebsocketMessage = z.object({
  data: LegacyMessageData,
  type: z.literal(SocketMessageType.LEGACY),
});

const BalancesSnapshotErrorMessage = z.object({
  data: BalanceSnapshotError,
  type: z.literal(SocketMessageType.BALANCES_SNAPSHOT_ERROR),
});

const TransactionStatusMessage = z.object({
  data: UnifiedTransactionStatusData,
  type: z.literal(SocketMessageType.TRANSACTION_STATUS),
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

const DataMigrationStatusMessage = z.object({
  data: DataMigrationStatusData,
  type: z.literal(SocketMessageType.DATA_MIGRATION_STATUS),
});

const MigratedAccountsMessage = z.object({
  data: MigratedAddresses,
  type: z.literal(SocketMessageType.EVM_ACCOUNTS_DETECTION),
});

const NewTokenDetectedMessage = z.object({
  data: NewDetectedToken,
  type: z.literal(SocketMessageType.NEW_TOKEN_DETECTED),
});

const MissingApiKeyMessage = z.object({
  data: MissingApiKey,
  type: z.literal(SocketMessageType.MISSING_API_KEY),
});

const RefreshBalancesMessage = z.object({
  data: RefreshBalancesData,
  type: z.literal(SocketMessageType.REFRESH_BALANCES),
});

const DbUploadResultMessage = z.object({
  data: DbUploadResult,
  type: z.literal(SocketMessageType.DB_UPLOAD_RESULT),
});

const AccountingRuleConflictMessage = z.object({
  data: AccountingRuleConflictData,
  type: z.literal(SocketMessageType.ACCOUNTING_RULE_CONFLICT),
});

const CalendarReminderMessage = z.object({
  data: CalendarEventWithReminder,
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

const SolanaTokensMigrationMessage = z.object({
  data: SolanaTokensMigrationData,
  type: z.literal(SocketMessageType.SOLANA_TOKENS_MIGRATION),
});

const BinancePairsMissingMessage = z.object({
  data: BinancePairsMissingData,
  type: z.literal(SocketMessageType.BINANCE_PAIRS_MISSING),
});

const DatabaseUploadProgressMessage = z.object({
  data: DatabaseUploadProgress,
  type: z.literal(SocketMessageType.DATABASE_UPLOAD_PROGRESS),
});

export const WebsocketMessage = z.discriminatedUnion('type', [
  LegacyWebsocketMessage,
  BalancesSnapshotErrorMessage,
  TransactionStatusMessage,
  HistoryEventsStatusMessage,
  PremiumStatusUpdateMessage,
  DbUpgradeStatusMessage,
  DataMigrationStatusMessage,
  MigratedAccountsMessage,
  NewTokenDetectedMessage,
  MissingApiKeyMessage,
  RefreshBalancesMessage,
  DbUploadResultMessage,
  AccountingRuleConflictMessage,
  CalendarReminderMessage,
  ExchangeUnknownAssetMessage,
  ProgressUpdatesMessage,
  GnosisPaySessionKeyExpiredMessage,
  SolanaTokensMigrationMessage,
  BinancePairsMissingMessage,
  DatabaseUploadProgressMessage,
]);

export type WebsocketMessage = z.infer<typeof WebsocketMessage>;

export interface CommonMessageHandler<T> {
  handle: (data: T) => Promise<Notification | null>;
}
