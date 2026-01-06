import { z } from 'zod/v4';

export const HistoricalBalancesResponse = z.object({
  processingRequired: z.boolean(),
  entries: z.record(z.string(), z.string()).optional().default({}),
});

export type HistoricalBalancesResponse = z.infer<typeof HistoricalBalancesResponse>;

export interface HistoricalBalancesPayload {
  timestamp: number;
  asset?: string;
  location?: string;
  locationLabel?: string;
  protocol?: string;
}
