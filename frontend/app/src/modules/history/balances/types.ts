import { NumericString } from '@rotki/common';
import { z } from 'zod';

export const HistoricalBalancesAtEventsResponse = z.object({
  entries: z.record(z.string(), z.object({
    processingRequired: z.boolean(),
    buckets: z.array(z.object({
      location: z.string(),
      protocol: z.string().nullable(),
      balance: NumericString,
    })),
  })),
});

export type HistoricalBalancesAtEventsResponse = z.infer<typeof HistoricalBalancesAtEventsResponse>;

const HistoricalBalanceEntry = z.object({
  location: z.string(),
  locationLabel: z.string().nullish(),
  protocol: z.string().nullish(),
  asset: z.string(),
  amount: NumericString,
});

export type HistoricalBalanceEntry = z.infer<typeof HistoricalBalanceEntry>;

export const HistoricalBalancesResponse = z.object({
  processingRequired: z.boolean(),
  entries: z.array(HistoricalBalanceEntry).optional().default([]),
});

export type HistoricalBalancesResponse = z.infer<typeof HistoricalBalancesResponse>;

const HistoricalBalanceSeriesEntry = z.object({
  location: z.string(),
  locationLabel: z.string(),
  protocol: z.string().nullish(),
  asset: z.string(),
  times: z.array(z.number()),
  values: z.array(NumericString),
});

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

export const HistoricalBalanceDivergenceEvent = z.object({
  eventIdentifier: z.number(),
  groupIdentifier: z.string().nullable(),
  txHash: z.string().nullable(),
  timestamp: z.number(),
  blockNumber: z.number(),
  trackedBalance: NumericString,
  onchainBalance: NumericString,
  difference: NumericString,
});

export type HistoricalBalanceDivergenceEvent = z.infer<typeof HistoricalBalanceDivergenceEvent>;

const HistoricalBalanceDivergenceProbe = z.object({
  eventIndex: z.number(),
  matches: z.boolean(),
  event: HistoricalBalanceDivergenceEvent,
});

export const HistoricalBalanceDivergenceResponse = z.object({
  status: z.enum(['diverged', 'diverged_from_start', 'no_divergence', 'no_checkpoints']),
  location: z.string(),
  address: z.string(),
  asset: z.string(),
  totalEvents: z.number(),
  tolerance: NumericString,
  firstDiverged: HistoricalBalanceDivergenceEvent.nullable(),
  lastMatching: HistoricalBalanceDivergenceEvent.nullable(),
  probes: z.array(HistoricalBalanceDivergenceProbe),
});

export type HistoricalBalanceDivergenceResponse = z.infer<typeof HistoricalBalanceDivergenceResponse>;

export interface HistoricalBalanceDivergencePayload {
  evmChain: string;
  address: string;
  asset: string;
  tolerance?: string;
  /** Inclusive upper bound in seconds. */
  toTimestamp?: number;
}
