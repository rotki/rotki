import { NumericString } from '@rotki/common';
import { z } from 'zod';

const KrakenStakingEvent = z.object({
  eventType: z.enum([
    'receive',
    'staking receive asset',
    'staking deposit asset',
    'staking remove asset'
  ]),
  asset: z.string(),
  timestamp: z.number().nonnegative(),
  location: z.literal('kraken'),
  amount: NumericString,
  usdValue: NumericString
});

export type KrakenStakingEvent = z.infer<typeof KrakenStakingEvent>;

export const KrakenStakingEvents = z.array(KrakenStakingEvent);

export type KrakenStakingEvents = z.infer<typeof KrakenStakingEvents>;

export type KrakenStakingPagination = {
  limit: number;
  offset: number;
  orderByAttribute: keyof KrakenStakingEvent;
  ascending: boolean;
  fromTimestamp?: number;
  toTimestamp?: number;
  onlyCache?: boolean;
};

export const emptyPagination = (): KrakenStakingPagination => ({
  offset: 0,
  limit: 0,
  ascending: false,
  orderByAttribute: 'timestamp'
});

export type KrakenStakingPaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof KrakenStakingEvent)[];
  sortDesc: boolean[];
};
