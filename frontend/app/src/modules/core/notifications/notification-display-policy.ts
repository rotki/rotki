import { Priority } from '@rotki/common';

/**
 * The priority a notification lands on when its caller does not classify itself.
 *
 * @remarks
 * `HIGH` preserves the behaviour the app shipped with, where anything reaching the dispatcher
 * interrupted unless it opted out. The target model in rotki#12942 is `NORMAL`, so that an
 * unclassified notification is stored rather than popped, but flipping this constant is a sweep
 * of every call site's intent rather than a policy change, and it belongs with the classification
 * work. It is a constant so that sweep is one edit.
 */
export const DEFAULT_PRIORITY = Priority.HIGH;

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
