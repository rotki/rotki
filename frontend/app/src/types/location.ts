import type { ActionDataEntry } from '@/types/action';
import { z } from 'zod/v4';

export type AllLocation = Record<
  string,
  Omit<ActionDataEntry, 'identifier'> & {
    isExchange?: boolean;
    exchangeDetails?: {
      isExchangeWithPassphrase?: boolean;
      isExchangeWithKey?: boolean;
      isExchangeWithoutApiSecret?: boolean;
      experimental?: boolean;
    };
  }
>;

export interface AllLocationResponse {
  locations: AllLocation;
}

export const LocationLabel = z.object({
  location: z.string(),
  locationLabel: z.string(),
});

export type LocationLabel = z.infer<typeof LocationLabel>;

export const LocationLabels = z.array(LocationLabel);
