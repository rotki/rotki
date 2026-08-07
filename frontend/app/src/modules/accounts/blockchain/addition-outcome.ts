import type { AccountAdditionFailure, AdditionSummary } from '@/modules/accounts/use-account-addition-service';
import { errorOf } from '@/modules/core/tasks/task-result';

/**
 * Reading an {@link AdditionSummary} the way a form has to. Additions report every outcome as a
 * value rather than a throw, so a caller that only wraps the call in `try/catch` sees success for
 * all three of "added", "rejected" and "cancelled".
 *
 * Pure and message-agnostic: the caller supplies the already-translated fallback, so this stays
 * free of `useI18n` and can be tested without one.
 */

/**
 * The error to report when an addition added nothing. A single failure hands back its own cause, so
 * a backend field-level rejection still reaches the form as an `ApiValidationError` and highlights
 * the offending field; flattening it into a bare `Error` would show one generic toast instead.
 *
 * Several failures have no single field to highlight, so they get `fallback` and the mechanism's own
 * notification lists the addresses.
 */
export function additionError(failed: readonly AccountAdditionFailure[], fallback: string): Error {
  if (failed.length === 1)
    return errorOf(failed[0].error);

  return new Error(fallback);
}

/**
 * Nothing was added and every unit was cancelled. Not a success: treating it as one closes the
 * dialog, emits `complete` and refreshes for an account that was never added, discarding what the
 * user typed. Not an error either — the user asked for it, so nothing is reported.
 */
export function isNothingButCancelled(summary: AdditionSummary): boolean {
  return summary.added.length === 0 && summary.failed.length === 0 && summary.cancelled;
}
