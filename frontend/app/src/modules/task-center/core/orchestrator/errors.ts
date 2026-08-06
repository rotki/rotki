import { tag } from 'plainfp/tagged';

/**
 * Tagged outcomes for control commands (cancel / rerun). Returned inside a plainfp `Result`
 * so callers (the controller, then the UI) discriminate exhaustively without try/catch.
 */

/** No activity with the given id is known to the orchestrator. */
export const NotFound = tag('NotFound');

/** The activity already finished (complete/cancelled/failed) — nothing to cancel. */
export const AlreadyTerminal = tag('AlreadyTerminal');

/** The activity is running but exposes no cancel handle, so it cannot be interrupted. */
export const NotCancellable = tag('NotCancellable');

/** Rerun was asked for an activity that is still queued or running. */
export const NotRerunnable = tag('NotRerunnable');

export type ControlError =
  | ReturnType<typeof NotFound<{ id: string }>>
  | ReturnType<typeof AlreadyTerminal<{ id: string }>>
  | ReturnType<typeof NotCancellable<{ id: string }>>
  | ReturnType<typeof NotRerunnable<{ id: string }>>;
