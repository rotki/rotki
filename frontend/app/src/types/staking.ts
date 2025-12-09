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
  totalValue: NumericString,
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

export const LidoCsmNodeOperatorPayloadSchema = z.object({
  address: z.string(),
  nodeOperatorId: z.number().int().nonnegative(),
});

export type LidoCsmNodeOperatorPayload = z.infer<typeof LidoCsmNodeOperatorPayloadSchema>;

const LidoCsmOperatorTypeSchema = z.object({
  id: z.number().int().optional(),
  label: z.string().optional(),
}).strict().partial();

const LidoCsmBondSchema = z.object({
  claimable: NumericString.optional(),
  current: NumericString.optional(),
  required: NumericString.optional(),
}).strict().partial();

const LidoCsmKeysSchema = z.object({
  totalDeposited: z.number().int().nonnegative().optional(),
}).strict().partial();

const LidoCsmRewardsSchema = z.object({
  pending: NumericString.optional(),
}).strict().partial();

export const LidoCsmNodeOperatorMetricsSchema = z.object({
  bond: LidoCsmBondSchema.nullish(),
  keys: LidoCsmKeysSchema.nullish(),
  operatorType: LidoCsmOperatorTypeSchema.nullish(),
  rewards: LidoCsmRewardsSchema.nullish().optional(),
});

export type LidoCsmNodeOperatorMetrics = z.infer<typeof LidoCsmNodeOperatorMetricsSchema>;

export const LidoCsmNodeOperatorSchema = LidoCsmNodeOperatorPayloadSchema.extend({
  metrics: LidoCsmNodeOperatorMetricsSchema.nullish(),
});

export type LidoCsmNodeOperator = z.infer<typeof LidoCsmNodeOperatorSchema>;

export const LidoCsmNodeOperatorListSchema = z.array(LidoCsmNodeOperatorSchema);
