import { NumericString } from '@rotki/common';
import { z } from 'zod/v4';

export const HistoricalBalancesResponse = z.object({
  processingRequired: z.boolean(),
  entries: z.record(z.string(), NumericString).optional().default({}),
});

export type HistoricalBalancesResponse = z.infer<typeof HistoricalBalancesResponse>;

export interface HistoricalBalancesPayload {
  timestamp: number;
  asset?: string;
  location?: string;
  locationLabel?: string;
  protocol?: string;
}

export const HistoricalBalanceSeriesEntry = z.object({
  location: z.string(),
  locationLabel: z.string(),
  protocol: z.string().nullish(),
  asset: z.string(),
  times: z.array(z.number()),
  values: z.array(NumericString),
});

export type HistoricalBalanceSeriesEntry = z.infer<typeof HistoricalBalanceSeriesEntry>;

export const HistoricalBalanceSeriesResponse = z.object({
  processingRequired: z.boolean(),
  entries: z.array(HistoricalBalanceSeriesEntry).optional().default([]),
});

export type HistoricalBalanceSeriesResponse = z.infer<typeof HistoricalBalanceSeriesResponse>;

export interface HistoricalBalanceSeriesPayload {
  asset: string;
  locationLabel: string;
  location?: string;
  protocol?: string;
  fromTimestamp?: number;
  toTimestamp?: number;
}

export const OnchainHistoricalBalanceResponse = z.record(z.string(), NumericString);

export type OnchainHistoricalBalanceResponse = z.infer<typeof OnchainHistoricalBalanceResponse>;

export interface OnchainHistoricalBalancePayload {
  timestamp: number;
  evmChain: string;
  address: string;
  asset: string;
}

export const HistoricalBalanceSource = {
  HISTORICAL_EVENTS: 'historical_events',
  ARCHIVE_NODE: 'archive_node',
} as const;

export type HistoricalBalanceSource = typeof HistoricalBalanceSource[keyof typeof HistoricalBalanceSource];
