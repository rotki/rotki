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
