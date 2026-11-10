import { NumericString } from '@rotki/common';
import { z } from 'zod';

/**
 * The five states the backend classifier reports.
 *
 * @remarks
 * The UI shows four labels: `pending` and `not_compared` both read as "Not checked", because the
 * reason sentence, not a second grey label, tells the user which one it is.
 */
export const BucketStatus = z.enum([
  'reconciled',
  'mismatch',
  'blocked',
  'pending',
  'not_compared',
]);

export type BucketStatus = z.infer<typeof BucketStatus>;

/**
 * Why a bucket is in the state it is in.
 *
 * @remarks
 * Kept as a plain string rather than an enum: the evidence step may add freshness reasons after
 * this contract was frozen, and a new reason must not make the whole page fail to parse. The UI
 * knows the reasons it can explain and falls back to a generic sentence for the rest.
 */
const BucketReason = z.string();

/**
 * The saved comparison behind a reconciled or mismatched row.
 *
 * @remarks
 * These amounts are the ones the verdict was made from. They are deliberately separate from the
 * current bucket amounts: pairing a newer observation with an older verdict would show a check
 * that never ran.
 */
const BucketCheck = z.object({
  derivedBalance: NumericString,
  observedBalance: NumericString,
  /** Unix seconds; when the observed balance was queried. */
  observedAt: z.number(),
  /** Unix seconds; when the comparison was saved. */
  comparedAt: z.number(),
  /** Signed `observed - derived`, as computed by the backend. */
  delta: NumericString,
});

/** The event that stopped balance processing for a blocked bucket. */
const BucketStop = z.object({
  eventIdentifier: z.number(),
  /** Unix milliseconds. */
  eventTimestamp: z.number(),
  derivedBalanceBeforeEvent: NumericString,
  negativeAmount: NumericString,
  /**
   * The stopping event's group, so the events view can page to it and highlight it. Null only
   * when the event was deleted after the stop was recorded.
   */
  groupIdentifier: z.string().nullable(),
});

export const ReconciliationBucket = z.object({
  protocol: z.string().nullable(),
  asset: z.string(),
  status: BucketStatus,
  reasons: z.array(BucketReason),
  /** Current derived amount, null when no metric exists. Never replaced by zero. */
  derivedBalance: NumericString.nullable(),
  /** Current observed amount, null when no observation exists. */
  observedBalance: NumericString.nullable(),
  /** Unix seconds. */
  observedAt: z.number().nullable(),
  /** Unix milliseconds. */
  lastEventTs: z.number().nullable(),
  issueId: z.number().nullable(),
  check: BucketCheck.nullable(),
  stop: BucketStop.nullable(),
});

export type ReconciliationBucket = z.infer<typeof ReconciliationBucket>;

/** Buckets per status. Used both for the global totals and for one account's counts. */
export const StatusCounts = z.object({
  reconciled: z.number(),
  mismatch: z.number(),
  blocked: z.number(),
  pending: z.number(),
  notCompared: z.number(),
});

export type StatusCounts = z.infer<typeof StatusCounts>;

export const ReconciliationPagination = z.object({
  limit: z.number(),
  offset: z.number(),
  /** Rows matching the status filter. */
  total: z.number(),
});

export type ReconciliationPagination = z.infer<typeof ReconciliationPagination>;

export const ReconciliationAccount = z.object({
  location: z.string(),
  locationLabel: z.string().nullable(),
  isExchange: z.boolean(),
  /** Every bucket of the account; the `status` filter never changes these counts. */
  counts: StatusCounts,
  /** Unix seconds, null when nothing was compared yet. */
  lastComparedAt: z.number().nullable(),
  /** Unix milliseconds. */
  lastEventTs: z.number().nullable(),
  /** Unix seconds, null when history sync coverage is unavailable. */
  historySyncedTo: z.number().nullable(),
  /** Present only for an account-scoped request. */
  buckets: z.array(ReconciliationBucket).optional(),
  pagination: ReconciliationPagination.optional(),
});

export type ReconciliationAccount = z.infer<typeof ReconciliationAccount>;

export const ReconciliationResponse = z.object({
  /** STALE_BALANCES_FROM_TS is set. */
  stale: z.boolean(),
  /** Historical balance processing is running. */
  processing: z.boolean(),
  /** Global counts, unfiltered by `status`. */
  totals: StatusCounts,
  bucketsTotal: z.number(),
  accounts: z.array(ReconciliationAccount),
});

export type ReconciliationResponse = z.infer<typeof ReconciliationResponse>;

export interface ReconciliationRequest {
  location?: string;
  locationLabel?: string;
  status?: BucketStatus[];
  limit?: number;
  offset?: number;
}
