import { NumericString } from '@rotki/common';
import { z } from 'zod';

export const CostBasisDirection = {
  RECEIVE: 'receive',
  SPEND: 'spend',
} as const;

/** The cost basis method whose spends share one average basis rather than matching single lots. */
export const AVERAGE_COST_BASIS_METHOD = 'acb';

const CostBasisBucket = z.object({
  asset: z.string(),
  location: z.string(),
  locationLabel: z.string().nullable(),
  method: z.string(),
  protocol: z.string().nullable(),
});

/** The history event that acquired a lot. Its timestamp is in milliseconds. */
const CostBasisAcquisition = z.object({
  groupIdentifier: z.string(),
  identifier: z.number(),
  location: z.string(),
  locationLabel: z.string().nullable(),
  timestamp: z.number(),
});

const CostBasisLot = z.object({
  /** Seconds. */
  acquiredAt: z.number(),
  /** Null when the acquiring event no longer exists. */
  acquisition: CostBasisAcquisition.nullable(),
  amount: NumericString,
  basisPerUnit: NumericString,
  lotId: z.string(),
  /** False when the lot was held for longer than the tax free period. */
  taxable: z.boolean(),
});

export type CostBasisLot = z.infer<typeof CostBasisLot>;

const CostBasisReceive = CostBasisBucket.extend({
  basisPerUnit: NumericString,
  basisSource: z.string(),
  direction: z.literal(CostBasisDirection.RECEIVE),
  lotIds: z.array(z.string()),
});

export type CostBasisReceive = z.infer<typeof CostBasisReceive>;

const CostBasisSpend = CostBasisBucket.extend({
  basisRemaining: NumericString,
  basisRemoved: NumericString,
  direction: z.literal(CostBasisDirection.SPEND),
  lots: z.array(CostBasisLot),
  /** Null when what was spent has no known worth, as for a move between two own accounts or an unpriced spend. */
  proceeds: NumericString.nullable(),
  /** Null when the spend could not be priced. */
  realizedPnl: NumericString.nullable(),
  taxfreePnl: NumericString.nullable(),
});

export type CostBasisSpend = z.infer<typeof CostBasisSpend>;

const CostBasisEntry = z.discriminatedUnion('direction', [CostBasisReceive, CostBasisSpend]);

export type CostBasisEntry = z.infer<typeof CostBasisEntry>;

export const EventsCostBasisResponse = z.object({
  /** Keyed by event identifier. Events that affect no lots or are in `stale` are absent. */
  entries: z.record(z.string(), z.array(CostBasisEntry)),
  method: z.string(),
  /** Requested event identifiers whose cost basis waits to be processed. */
  stale: z.array(z.number()),
});

export type EventsCostBasisResponse = z.infer<typeof EventsCostBasisResponse>;
