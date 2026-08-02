import { ActivityKind } from '../types';

/**
 * The kind of history-event mutation that just succeeded. Emitted on the task-center bus by
 * the existing mutation sites; mapped here to the work it invalidates. Enumerified so emit
 * sites and the policy share constants, never literals.
 */
export const EditKind = {
  /** A history event (or group) was deleted, or excluded from accounting. */
  EVENT_DELETED: 'event-deleted',
  /** An asset movement was unlinked from its group. */
  EVENT_UNLINKED: 'event-unlinked',
  /** A transaction's events were re-decoded. */
  EVENT_REDECODED: 'event-redecoded',
  /** A transaction (and its events) was deleted. */
  TRANSACTION_DELETED: 'transaction-deleted',
} as const;

export type EditKind = (typeof EditKind)[keyof typeof EditKind];

/**
 * Every event mutation makes a computed P&L report and any historical balance series stale,
 * so an edit should offer to re-run them (issue #6825). Decoding/balances are *driven by* the
 * mutation itself (the redecode action re-decodes), so they are deliberately not listed here —
 * only the downstream work the user has to re-trigger.
 *
 * NOTE: `PNL_REPORT` is intentionally deferred for now. It runs native and is re-runnable from the
 * task center, but is kept out of smart re-run while the behaviour is validated — re-add
 * `ActivityKind.PNL_REPORT` here to switch it on.
 */
const COMPUTED_DOWNSTREAM: readonly ActivityKind[] = [
  ActivityKind.HISTORICAL_BALANCES,
];

/**
 * Pure map from an {@link EditKind} to the {@link ActivityKind}s it invalidates. No Vue, no
 * store — unit-tested with literal inputs. Returns an empty list for an unknown edit so the
 * caller never has to guard.
 */
const EDIT_INVALIDATES: Record<EditKind, readonly ActivityKind[]> = {
  [EditKind.EVENT_DELETED]: COMPUTED_DOWNSTREAM,
  [EditKind.EVENT_REDECODED]: COMPUTED_DOWNSTREAM,
  [EditKind.EVENT_UNLINKED]: COMPUTED_DOWNSTREAM,
  [EditKind.TRANSACTION_DELETED]: COMPUTED_DOWNSTREAM,
};

/** Activity kinds invalidated by a history-event mutation; empty for an unknown edit. */
export function invalidatedKinds(edit: EditKind): readonly ActivityKind[] {
  return EDIT_INVALIDATES[edit] ?? [];
}
