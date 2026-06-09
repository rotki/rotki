import { NumericString } from '@rotki/common';
import { z } from 'zod/v4';

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
