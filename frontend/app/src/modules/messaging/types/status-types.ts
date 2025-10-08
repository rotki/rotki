import { CommonQueryStatusData } from '@rotki/common';
import { z } from 'zod/v4';
import { EvmChainLikeAddress } from '@/types/history/events';
import { SocketMessageProgressUpdateSubType } from './base';

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

export const MigratedAddresses = z.array(EvmChainLikeAddress);

export type MigratedAddresses = z.infer<typeof MigratedAddresses>;

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
  status: z.enum(HistoryEventsQueryStatus),
});

export type HistoryEventsQueryData = z.infer<typeof HistoryEventsQueryData>;

export const TransactionsQueryStatus = {
  ACCOUNT_CHANGE: 'account_change',
  DECODING_TRANSACTIONS_FINISHED: 'decoding_transactions_finished',
  DECODING_TRANSACTIONS_STARTED: 'decoding_transactions_started',
  QUERYING_EVM_TOKENS_TRANSACTIONS: 'querying_evm_tokens_transactions',
  QUERYING_INTERNAL_TRANSACTIONS: 'querying_internal_transactions',
  QUERYING_TRANSACTIONS: 'querying_transactions',
  QUERYING_TRANSACTIONS_FINISHED: 'querying_transactions_finished',
  QUERYING_TRANSACTIONS_STARTED: 'querying_transactions_started',
} as const;

export type TransactionsQueryStatus = (typeof TransactionsQueryStatus)[keyof typeof TransactionsQueryStatus];

export const EvmTransactionStatusData = z.object({
  address: z.string(),
  chain: z.string(),
  period: z.tuple([z.number(), z.number()]),
  status: z.enum(TransactionsQueryStatus),
  subtype: z.literal('evm').or(z.literal('evmlike')),
});

export const BitcoinTransactionStatusData = z.object({
  addresses: z.array(z.string()),
  chain: z.string(),
  status: z.enum(TransactionsQueryStatus),
  subtype: z.literal('bitcoin'),
});

export const SolanaTransactionStatusData = z.object({
  address: z.string(),
  chain: z.string(),
  period: z.tuple([z.number(), z.number()]),
  status: z.enum(TransactionsQueryStatus),
  subtype: z.literal('solana'),
});

export const UnifiedTransactionStatusData = z.union([
  EvmTransactionStatusData,
  BitcoinTransactionStatusData,
  SolanaTransactionStatusData,
]);

export type UnifiedTransactionStatusData = z.infer<typeof UnifiedTransactionStatusData>;

// Progress update related types
export const EvmUnDecodedTransactionsData = CommonQueryStatusData.extend({
  chain: z.string(),
});

export type EvmUnDecodedTransactionsData = z.infer<typeof EvmUnDecodedTransactionsData>;

export const EvmUndecodedTransactionBreakdown = z.object({
  total: z.number(),
  undecoded: z.number(),
});

export const EvmUndecodedTransactionResponse = z.record(z.string(), EvmUndecodedTransactionBreakdown);

export type EvmUndecodedTransactionResponse = z.infer<typeof EvmUndecodedTransactionResponse>;

export const EvmUnDecodedTransactionsDataWithSubtype = EvmUnDecodedTransactionsData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.UNDECODED_TRANSACTIONS),
});

export const StatsPriceQueryData = CommonQueryStatusData.extend({
  counterparty: z.string(),
});

export type StatsPriceQueryData = z.infer<typeof StatsPriceQueryData>;

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

export const HistoricalPriceQueryStatusDataWithSubtype = CommonQueryStatusData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.HISTORICAL_PRICE_QUERY_STATUS),
});

export const ProtocolCacheUpdatesData = EvmUnDecodedTransactionsData.extend({
  protocol: z.string(),
});

export type ProtocolCacheUpdatesData = z.infer<typeof ProtocolCacheUpdatesData>;

export const ProtocolCacheUpdatesDataWithSubtype = ProtocolCacheUpdatesData.extend({
  subtype: z.literal(SocketMessageProgressUpdateSubType.PROTOCOL_CACHE_UPDATES),
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
