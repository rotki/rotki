import type { EditKind } from '../core/rerun/policy';
import mitt from 'mitt';

/**
 * Payload of a `TaskCenterBusEvents['event:mutated']` signal: which kind of history event mutation
 * succeeded.
 *
 * @remarks
 * `use-smart-rerun` maps it through the pure re-run policy to the work that needs re-running
 * (issue #6825).
 */
export interface EventMutated {
  readonly kind: EditKind;
}

/**
 * Decoupling bus between the history-event mutation sites and the Task Center. Producers emit
 * `event:mutated` at their existing success points; `use-smart-rerun` is the only subscriber.
 * Modeled on the sigil bus — a void-ish signal carrying just enough to drive a policy, never a
 * data channel.
 */
// eslint-disable-next-line @typescript-eslint/consistent-type-definitions -- mitt requires a type alias, not an interface
type TaskCenterBusEvents = {
  /** A history event was deleted / unlinked / re-decoded (see {@link EventMutated}). */
  'event:mutated': EventMutated;
};

export const taskCenterBus = mitt<TaskCenterBusEvents>();
