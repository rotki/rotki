import { AssetBalance, NumericString } from '@rotki/common';
import { z } from 'zod/v4';

enum KrakenStakingEventType {
  REWARD = 'reward',
  RECEIVE_WRAPPED = 'receive wrapped',
  DEPOSIT_ASSET = 'deposit asset',
  REMOVE_ASSET = 'remove asset',
}

const KrakenStakingEventTypeEnum = z.enum(KrakenStakingEventType);

const KrakenStakingEvent = AssetBalance.extend({
  eventType: KrakenStakingEventTypeEnum,
  location: z.literal('kraken'),
  timestamp: z.number().nonnegative(),
});

type KrakenStakingEvent = z.infer<typeof KrakenStakingEvent>;

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
  id: z.number().int(),
  label: z.string(),
});

const LidoCsmBondSchema = z.object({
  claimable: NumericString,
  current: NumericString,
  required: NumericString,
});

const LidoCsmKeysSchema = z.object({
  totalDeposited: z.number().int().nonnegative(),
});

const LidoCsmRewardsSchema = z.object({
  pending: NumericString,
});

const LidoCsmNodeOperatorMetricsSchema = z.object({
  bond: LidoCsmBondSchema,
  keys: LidoCsmKeysSchema,
  operatorType: LidoCsmOperatorTypeSchema,
  rewards: LidoCsmRewardsSchema,
});

const LidoCsmNodeOperatorSchema = LidoCsmNodeOperatorPayloadSchema.extend({
  metrics: LidoCsmNodeOperatorMetricsSchema.nullable(),
});

export type LidoCsmNodeOperator = z.infer<typeof LidoCsmNodeOperatorSchema>;

export const LidoCsmNodeOperatorListSchema = z.array(LidoCsmNodeOperatorSchema);
