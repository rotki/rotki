import { NumericString } from '@rotki/common';
import { z } from 'zod';

export enum KrakenStakingEventType {
  REWARD = 'reward',
  RECEIVE_WRAPPED = 'receive wrapped',
  DEPOSIT_ASSET = 'deposit asset',
  REMOVE_ASSET = 'remove asset',
}

export const KrakenStakingEventTypeEnum = z.nativeEnum(KrakenStakingEventType);

const KrakenStakingEvent = z.object({
  amount: NumericString,
  asset: z.string(),
  eventType: KrakenStakingEventTypeEnum,
  location: z.literal('kraken'),
  timestamp: z.number().nonnegative(),
  usdValue: NumericString,
});

export type KrakenStakingEvent = z.infer<typeof KrakenStakingEvent>;

const ReceivedAmount = z.object({
  amount: NumericString,
  asset: z.string(),
  usdValue: NumericString,
});

export type ReceivedAmount = z.infer<typeof ReceivedAmount>;

export const KrakenStakingEvents = z.object({
  assets: z.array(z.string()),
  entriesFound: z.number().nonnegative(),
  entriesLimit: z.number().min(-1),
  entriesTotal: z.number().nonnegative(),
  received: z.array(ReceivedAmount),
  totalUsdValue: NumericString,
});

export type KrakenStakingEvents = z.infer<typeof KrakenStakingEvents>;

export interface KrakenStakingPagination {
  limit: number;
  offset: number;
  orderByAttributes: (keyof KrakenStakingEvent)[];
  ascending: boolean[];
  fromTimestamp?: number;
  toTimestamp?: number;
  asset?: string;
  eventSubtypes?: string[];
  onlyCache?: boolean;
}

export type KrakenStakingDateFilter = Pick<KrakenStakingPagination, 'fromTimestamp' | 'toTimestamp'>;

export function emptyPagination(): KrakenStakingPagination {
  return {
    ascending: [false],
    limit: 0,
    offset: 0,
    orderByAttributes: ['timestamp'],
  };
}
