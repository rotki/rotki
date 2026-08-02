import type { Result } from 'plainfp/result';
import type { Activity, ActivityId, ActivityKind, ActivitySteps, GroupId, WorkStatus } from '../types';
import type { ControlError } from './errors';
import type { EligibilityRule } from './rules';
import type { ActivitySpec, LaneCaps, LaneFamilyActiveCaps, LaneFamilyCaps } from './spec';

/**
 * The Task Center's execution spine, as a contract. Separated from the implementation so the
 * surface producers and the reactive shell code against can be read on its own.
 */
export interface TaskOrchestrator {
  /** Register and schedule a unit of work; returns its id. */
  readonly submit: <T>(spec: ActivitySpec<T>) => ActivityId;
  /** Cancel one activity (drop if queued, abort if running). */
  readonly cancel: (id: ActivityId) => Result<void, ControlError>;
  /** Cancel every non-terminal activity in a group (issue #10955). */
  readonly cancelGroup: (group: GroupId) => void;
  /** Cancel every non-terminal activity of a kind. */
  readonly cancelByKind: (kind: ActivityKind) => void;
  /**
   * Cancel every non-terminal activity whose id extends `kind:parts` — the cancel-side sibling of
   * {@link statusOfPrefix}. Per-request producers give each submission its own id, so an exact-id
   * cancel can't express "abort whatever historic-price lookups are in flight"; matching on a
   * separator boundary keeps it narrower than {@link cancelByKind}.
   */
  readonly cancelByPrefix: (kind: ActivityKind, ...parts: (string | number)[]) => void;
  /** Cancel every non-terminal activity. */
  readonly cancelAll: () => void;
  /** Re-run a terminal, rerunnable activity using its original spec. */
  readonly rerun: (id: ActivityId) => Result<void, ControlError>;
  /**
   * Push step progress to a running activity from an external source — e.g. a backend websocket
   * that streams progress for work the producer fired once. No-op unless the activity is currently
   * running. The internal `report` handed to a spec's `run` funnels through here too.
   */
  readonly reportProgress: (id: ActivityId, steps: ActivitySteps) => void;
  /**
   * Push progress onto every running activity under `kind:parts`. For progress that arrives
   * globally (a websocket status with no request identity) while the producer gives each request
   * its own id, so no exact id is known at the push site.
   */
  readonly reportProgressByPrefix: (steps: ActivitySteps, kind: ActivityKind, ...parts: (string | number)[]) => void;
  /** Current activities projected to the shared {@link Activity} model. */
  readonly snapshot: () => Activity[];
  /**
   * Projected liveness + freshness for a kind, or — when `parts` are given — the specific
   * activity `makeActivityId(kind, ...parts)`. The single replacement for `useStatusUpdater`.
   */
  readonly statusOf: (kind: ActivityKind, ...parts: (string | number)[]) => WorkStatus;
  /**
   * Projected liveness + freshness aggregated over every activity whose id extends
   * `kind:parts` — the coarse read for per-request producers (one activity per query), where
   * an exact-id lookup would never match and a whole-kind aggregate would be too broad.
   */
  readonly statusOfPrefix: (kind: ActivityKind, ...parts: (string | number)[]) => WorkStatus;
  /**
   * Record a completion for data that arrived without any work — a session restore reading a
   * cached snapshot, say. Writes the ledger only: liveness comes from the live records, so a
   * marked id reads as "we have data" without ever having looked active.
   */
  readonly markCompleted: (kind: ActivityKind, ...parts: (string | number)[]) => void;
  /**
   * Drop the recorded completion of every id under `kind:parts` — the freshness-side sibling of
   * {@link cancelByPrefix}. `everCompleted` flips back to false, so the next guarded fetch is
   * admitted.
   */
  readonly invalidate: (kind: ActivityKind, ...parts: (string | number)[]) => void;
  /** Subscribe to state changes; returns an unsubscribe fn. */
  readonly onChange: (listener: () => void) => () => void;
  /** Drop finished activities (the UI keeps a short tail; this prunes the rest). Keeps the ledger. */
  readonly clearTerminal: () => void;
  /** Session boundary: wipe live records, the queue and the completion ledger (logout). */
  readonly reset: () => void;
}

export interface OrchestratorOptions {
  readonly caps?: LaneCaps;
  /** Caps for lanes minted per entity (one per chain, …) that cannot be named up front. */
  readonly laneFamilies?: LaneFamilyCaps;
  /** How many distinct lanes of a family may run at once — the nesting a pre-submitted tree loses. */
  readonly laneFamilyActive?: LaneFamilyActiveCaps;
  readonly defaultCap?: number;
  readonly rules?: readonly EligibilityRule[];
  /** Injectable clock (defaults to `Date.now`) so tests get deterministic `startedAt`. */
  readonly now?: () => number;
}
