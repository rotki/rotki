import { Priority } from '@rotki/common';

/**
 * The priority a notification lands on when its caller does not classify itself.
 *
 * @remarks
 * `NORMAL` is the target model of rotki#12942: an unclassified notification is recorded in the
 * drawer rather than popped, so forgetting to classify costs a missed toast rather than an
 * unwanted interruption. Every producer in the tree was classified before this was flipped from
 * `HIGH`, so nothing relies on the default to interrupt.
 */
export const DEFAULT_PRIORITY = Priority.NORMAL;

/**
 * Whether a notification of this priority interrupts the user with a popup.
 *
 * @remarks
 * The single place the decision lives. `ACTION` is something only the user can resolve and `HIGH`
 * is the outcome of something they just did, so both interrupt; `NORMAL` and `BULK` are recorded
 * for the drawer and never pop. A caller may still suppress its own popup via `display: false`,
 * which is why this answers the default rather than the final value.
 */
export function displaysFor(priority: Priority = DEFAULT_PRIORITY): boolean {
  return priority >= Priority.HIGH;
}
