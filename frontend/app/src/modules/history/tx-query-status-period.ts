import {
  TransactionsQueryStatus,
  type UnifiedTransactionStatusData,
} from '@/modules/core/messaging/types';

/**
 * The queried range and the boundaries progress is measured against.
 *
 * Kept beside the pure functions that derive it rather than in the store, which only wires them to
 * incoming messages. `existing` is typed structurally here so this module stays independent of the
 * store's own entry union.
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
export function determineOriginalPeriodEnd(
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
 * - If period[0] > 0, uses that as the actual start
 * - If period[0] is 0 (beginning of time), captures the first non-zero period[1] as the effective start
 * - Preserves existing originalPeriodStart for subsequent updates
 * - Does not capture from STARTED status (where period[1] is the end boundary, not progress)
 */
export function determineOriginalPeriodStart(
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
 * ⚠️ The backend overloads that slot: it is the range's target end on STARTED, and the cursor
 * reached so far on every later message. Stored raw, STARTED reads as "already at the end" — it is
 * captured as `originalPeriodEnd` and compared against itself, so the bar renders 100% and the range
 * renders `to → to` before anything has been queried. Nothing has progressed yet, so the cursor
 * belongs at the start of the range.
 *
 * EVM hides this: its cursor advances within milliseconds, so the wrong value is never seen. Bitcoin
 * sends one cursor update per block-height batch, after that batch has already been queried, and
 * none at all when a batch comes back empty, so it shows the wrong value for the whole query.
 *
 * ⚠️ Callers must still pass the *raw* period to `determineOriginalPeriodEnd`, which is what makes
 * STARTED the message that establishes the target.
 */
export function periodWithCursorAtStart(
  status: TransactionsQueryStatus,
  period: [number, number],
): [number, number] {
  return status === TransactionsQueryStatus.QUERYING_TRANSACTIONS_STARTED ? [period[0], period[0]] : period;
}

/**
 * Period tracking for a bitcoin message, which is the one subtype whose `period` is optional.
 *
 * ⚠️ Carries `existing`'s values when the message has none: the entry is rebuilt from scratch per
 * message, so a period-less update would otherwise erase what an earlier one established and make
 * the progress bar vanish mid-query.
 */
export function bitcoinPeriodFields(
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
