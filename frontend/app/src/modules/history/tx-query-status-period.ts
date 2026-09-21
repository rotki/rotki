import {
  TransactionsQueryStatus,
  type UnifiedTransactionStatusData,
} from '@/modules/core/messaging/types';

/**
 * The queried range and the boundaries progress is measured against.
 *
 * Derived here by pure functions, one frame at a time; the transaction status handler only holds the
 * result for as long as the account's sync is live, and feeds each frame back in.
 */
export interface PeriodTracking {
  period: [number, number];
  originalPeriodEnd?: number;
  originalPeriodStart?: number;
}

/**
 * Determines the original period end value for progress tracking.
 * For STARTED status, captures the period[1] as the end boundary.
 * For subsequent updates, preserves the existing value.
 */
function determineOriginalPeriodEnd(
  status: TransactionsQueryStatus,
  period: [number, number],
  existing?: Partial<PeriodTracking>,
): number | undefined {
  if (status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED) {
    return period[1];
  }
  if (existing && 'originalPeriodEnd' in existing) {
    return existing.originalPeriodEnd;
  }
  return undefined;
}

/**
 * Determines the original period start value for progress tracking.
 *
 * @remarks
 * A non-zero `period[0]` is the actual start. When it is `0` (the beginning of time), the first
 * non-zero `period[1]` becomes the effective start instead. An existing `originalPeriodStart` is
 * preserved across later updates, and nothing is captured from STARTED, where `period[1]` is the end
 * boundary rather than progress.
 */
function determineOriginalPeriodStart(
  status: TransactionsQueryStatus,
  period: [number, number],
  existing?: Partial<PeriodTracking>,
): number | undefined {
  const [periodStart, periodCurrent] = period;

  if (periodStart > 0) {
    return periodStart;
  }
  if (existing && 'originalPeriodStart' in existing && existing.originalPeriodStart !== undefined) {
    return existing.originalPeriodStart;
  }
  if (periodCurrent > 0 && status !== TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED) {
    return periodCurrent;
  }
  return undefined;
}

/**
 * The stored period, with `period[1]` normalised to mean the query's current cursor.
 *
 * The backend overloads that slot: the range's target end on STARTED, the cursor reached so far
 * on every later message. Stored raw, STARTED reads as "already at the end", so the bar renders 100%
 * and the range `to → to` before anything is queried. EVM hides it (its cursor advances within
 * milliseconds); bitcoin shows the wrong value for the whole query.
 *
 * Callers must still pass the *raw* period to `determineOriginalPeriodEnd`, which is what makes
 * STARTED the message that establishes the target.
 */
function periodWithCursorAtStart(
  status: TransactionsQueryStatus,
  period: [number, number],
): [number, number] {
  return status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED ? [period[0], period[0]] : period;
}

/**
 * The queried range as step progress: how much of the window the backend has read, over the whole
 * window.
 *
 * @remarks
 * The unit is seconds of the queried range, not transactions. That is the only quantity these
 * messages carry, and it is what the sync panel has always drawn; naming it as steps puts it on the
 * activity itself instead of a projection beside it.
 *
 * `undefined` where the range cannot be measured, which is a real state rather than an edge case:
 * a query with no period at all (bitcoin sends none), one that has not yet established its target,
 * and one whose window is empty because there is nothing to catch up on. Each leaves the activity
 * indeterminate, which is honest, rather than claiming 0% or 100%.
 */
export function periodSteps(tracking: Partial<PeriodTracking>): { current: number; total: number } | undefined {
  const { originalPeriodEnd, originalPeriodStart, period } = tracking;
  if (period === undefined || originalPeriodEnd === undefined)
    return undefined;

  const start = originalPeriodStart ?? period[0];
  const total = originalPeriodEnd - start;
  if (total <= 0)
    return undefined;

  return { current: Math.min(Math.max(period[1] - start, 0), total), total };
}

/** One account's query, as the frames of its run have described it so far. */
export interface TxAccountTracking extends Partial<PeriodTracking> {
  readonly status: TransactionsQueryStatus;
}

/**
 * Folds one frame into an account's tracking.
 *
 * @remarks
 * `existing` is what earlier frames of the same run established, and `undefined` on the run's first
 * frame. A first frame that is not STARTED, the message that names the target, is measured against
 * the moment the account was first seen, so a query whose STARTED frame was missed still has a
 * window end instead of none. Bitcoin is left out of that: its frames may carry no period at all,
 * and an invented window would report progress nobody measured.
 *
 * @param data - The frame as the backend sent it; a bitcoin frame speaks for every address it lists.
 * @param existing - The account's tracking before this frame.
 * @param now - The current time, in seconds.
 * @returns The account's tracking after this frame.
 */
export function mergeTxFrame(
  data: UnifiedTransactionStatusData,
  existing: TxAccountTracking | undefined,
  now: number,
): TxAccountTracking {
  if (data.subtype === 'bitcoin')
    return { status: data.status, ...bitcoinPeriodFields(data, existing) };

  const before: Partial<PeriodTracking> = existing ?? { originalPeriodEnd: now, period: [0, now] };
  return {
    originalPeriodEnd: determineOriginalPeriodEnd(data.status, data.period, before),
    originalPeriodStart: determineOriginalPeriodStart(data.status, data.period, before),
    period: periodWithCursorAtStart(data.status, data.period),
    status: data.status,
  };
}

/**
 * Period tracking for a bitcoin message, which is the one subtype whose `period` is optional.
 *
 * Carries `existing`'s values when the message has none: the entry is rebuilt from scratch per
 * message, so a period-less update would otherwise erase what an earlier one established and make
 * the progress bar vanish mid-query.
 */
function bitcoinPeriodFields(
  data: Extract<UnifiedTransactionStatusData, { subtype: 'bitcoin' }>,
  existing?: Partial<PeriodTracking>,
): Partial<PeriodTracking> {
  if (data.period === undefined) {
    return {
      originalPeriodEnd: existing?.originalPeriodEnd,
      originalPeriodStart: existing?.originalPeriodStart,
      period: existing?.period,
    };
  }

  return {
    originalPeriodEnd: determineOriginalPeriodEnd(data.status, data.period, existing),
    originalPeriodStart: determineOriginalPeriodStart(data.status, data.period, existing),
    period: periodWithCursorAtStart(data.status, data.period),
  };
}
