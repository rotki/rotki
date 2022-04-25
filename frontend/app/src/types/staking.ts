import { NumericString } from '@rotki/common';
import { z } from 'zod';

export enum KrakenStakingEventType {
  REWARD = 'reward',
  RECEIVE_WRAPPED = 'receive wrapped',
  DEPOSIT_ASSET = 'deposit asset',
  REMOVE_ASSET = 'remove asset'
}

export const KrakenStakingEventTypeEnum = z.nativeEnum(KrakenStakingEventType);

const KrakenStakingEvent = z.object({
  eventType: KrakenStakingEventTypeEnum,
  asset: z.string(),
  timestamp: z.number().nonnegative(),
  location: z.literal('kraken'),
  amount: NumericString,
  usdValue: NumericString
});

export type KrakenStakingEvent = z.infer<typeof KrakenStakingEvent>;

const ReceivedAmount = z.object({
  amount: NumericString,
  usdValue: NumericString,
  asset: z.string()
});

export type ReceivedAmount = z.infer<typeof ReceivedAmount>;

export const KrakenStakingEvents = z.object({
  assets: z.array(z.string()),
  entriesFound: z.number().nonnegative(),
  entriesLimit: z.number().min(-1),
  entriesTotal: z.number().nonnegative(),
  events: z.array(KrakenStakingEvent),
  received: z.array(ReceivedAmount),
  totalUsdValue: NumericString
});

export type KrakenStakingEvents = z.infer<typeof KrakenStakingEvents>;

export type KrakenStakingPagination = {
  limit: number;
  offset: number;
  orderByAttribute: keyof KrakenStakingEvent;
  ascending: boolean;
  fromTimestamp?: string;
  toTimestamp?: string;
  asset?: string;
  eventSubtypes?: string[];
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
