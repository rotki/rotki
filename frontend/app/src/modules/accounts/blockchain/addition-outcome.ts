import type { AccountAdditionFailure, AdditionSummary } from '@/modules/accounts/use-account-addition-service';
import { isValidEthAddress } from '@rotki/common';
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
 * Several failures have no single field to highlight, so they get `fallback` and the task dock lists
 * the addresses.
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
 *
 * A skipped unit breaks the "nothing but": it ran to an answer, which the dock is showing, so the
 * dialog has nothing left to hold open for.
 */
export function isNothingButCancelled(summary: AdditionSummary): boolean {
  return summary.added.length === 0 && summary.failed.length === 0 && summary.skipped === 0 && summary.cancelled;
}

/**
 * Whether the form has to wait for an addition of these entries before it closes.
 *
 * @remarks
 * The form checks no address format, so the backend is the first to reject a mistyped address or an
 * unresolvable ENS name, and that rejection is input to correct, which belongs on the form. Only a
 * batch of well-formed hex addresses on a chain that takes them can no longer fail that way: every
 * other outcome of those is reported by the task dock, so the dialog closes on submit.
 *
 * `takesHex` says whether the target chain takes hex addresses: an EVM or EVM-like chain, or every
 * EVM chain at once.
 */
export function awaitsAddition(addresses: readonly string[], takesHex: boolean): boolean {
  return !takesHex || !addresses.every(address => isValidEthAddress(address));
}
