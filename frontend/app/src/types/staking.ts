import { AssetBalance, NumericString } from '@rotki/common';
import { z } from 'zod/v4';

export enum KrakenStakingEventType {
  REWARD = 'reward',
  RECEIVE_WRAPPED = 'receive wrapped',
  DEPOSIT_ASSET = 'deposit asset',
  REMOVE_ASSET = 'remove asset',
}

export const KrakenStakingEventTypeEnum = z.enum(KrakenStakingEventType);

const KrakenStakingEvent = AssetBalance.extend({
  eventType: KrakenStakingEventTypeEnum,
  location: z.literal('kraken'),
  timestamp: z.number().nonnegative(),
});

export type KrakenStakingEvent = z.infer<typeof KrakenStakingEvent>;

export const KrakenStakingEvents = z.object({
  assets: z.array(z.string()),
  entriesFound: z.number().nonnegative(),
  entriesLimit: z.number().min(-1),
  entriesTotal: z.number().nonnegative(),
  received: z.array(AssetBalance),
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

export interface LidoCsmNodeOperatorPayload {
  address: string;
  nodeOperatorId: number;
}

export interface LidoCsmNodeOperatorMetrics {
  operatorType: {
    id: number;
    label: string;
  } | null;
  bond: {
    current: string;
    required: string;
    claimable: string;
  } | null;
  keys: {
    totalDeposited: number;
  } | null;
  rewards?: {
    pending: string;
  } | null;
}

export interface LidoCsmNodeOperator extends LidoCsmNodeOperatorPayload {
  metrics?: LidoCsmNodeOperatorMetrics | null;
}
