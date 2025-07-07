import { CommonQueryStatusData } from '@rotki/common';
import { z } from 'zod/v4';
import { SocketMessageProgressUpdateSubType } from './base';
import { EvmUnDecodedTransactionsData, EvmUnDecodedTransactionsDataWithSubtype } from './transactions';

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
