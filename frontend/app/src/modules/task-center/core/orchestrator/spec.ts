import type { ResultAsync, RetryOptions } from 'plainfp/result-async';
import type { ActivityId, ActivityKind, ActivitySteps, ActivityText, GroupId } from '../types';
import type { TaskError } from '@/modules/core/tasks/task-result';

/**
 * Every lane whose name is fixed at author time. Declared as one closed list so a cap can only be
 * keyed by a lane that exists — a typo like `balnces` is a compile error rather than a silent
 * fallback to the default cap, which would otherwise surface only as unexplained concurrency.
 */
export const STATIC_LANES = ['default', 'balances', 'exchange', 'session', 'umbrella', 'chain-sync', 'decode'] as const;

export type StaticLane = (typeof STATIC_LANES)[number];

/**
 * Prefixes for lanes minted per entity, where the full name is only known at runtime
 * (`tx-sync:<chain>`). Also a closed list, so a family cap cannot be keyed by a prefix no producer
 * ever mints.
 */
export const LANE_FAMILIES = ['tx-sync:', 'exchange-events:', 'accounts-add:'] as const;

export type LaneFamily = (typeof LANE_FAMILIES)[number];

/** A lane minted from a family — the prefix is checked, the entity part is free. */
export type FamilyLane = `${LaneFamily}${string}`;

/** A concurrency lane. Activities in the same lane share a per-lane cap (see {@link LaneCaps}). */
export type Lane = StaticLane | FamilyLane;

/** Build a per-entity lane from a declared family, so the prefix can never drift from the caps. */
export function familyLane(family: LaneFamily, entity: string): FamilyLane {
  return `${family}${entity}`;
}

export const DEFAULT_LANE: StaticLane = 'default';

/**
 * Blockchain-balance refreshes + token detection run here; capped at 2 to mirror the old
 * `BalanceQueueService` `maxConcurrency`. Cached blockchain reads stay on {@link DEFAULT_LANE}
 * so initial load is not throttled.
 */
export const BALANCES_LANE: StaticLane = 'balances';

/** Exchange balance + savings queries run here; capped at 2, a pool separate from {@link BALANCES_LANE}. */
export const EXCHANGE_LANE: StaticLane = 'exchange';

/**
 * Unlocking a session — login and account creation. On its own lane because session work must
 * never queue behind user data: everything else in the app exists only once a session is up, so
 * sharing a pool with it means a stalled query can keep a user from signing in at all.
 */
export const SESSION_LANE: StaticLane = 'session';

/**
 * Umbrella activities that await children run here, never alongside them. A parent holding a slot in
 * the same lane as the children it waits for throttles them, and at a cap of 1 it would deadlock.
 * Nothing in this lane does work itself, so the cap only has to exceed the number of umbrellas.
 */
export const UMBRELLA_LANE: StaticLane = 'umbrella';

/** One per-chain sync group runs here; capped at 2, mirroring the old chain-level fan-out. */
export const CHAIN_SYNC_LANE: StaticLane = 'chain-sync';

/**
 * Every transaction decode runs here, capped at 2 — the parallelism the redecode paths always used
 * (`awaitParallelExecution(..., 2)`), now expressed once, in the lane, rather than by a limiter
 * wrapping a call that submits to a lane.
 *
 * ⚠️ It was briefly capped at 1, matching the sync path's old decode queue. That silently halved
 * redecode throughput: the redecode fan-outs were never migrated, so their outer limiter of 2 was
 * captured by the inner cap of 1 and became dead. One mechanism governs this now.
 */
export const DECODE_LANE: StaticLane = 'decode';

/**
 * Family prefix for the per-chain account lanes (`tx-sync:<chain>`). Capped per chain, so two
 * accounts sync at once *on each chain* rather than two across all of them.
 */
export const ACCOUNT_SYNC_LANE_PREFIX: LaneFamily = 'tx-sync:';

/**
 * Family prefix for the per-location exchange lanes (`exchange-events:<location>`). Capped at 1 per
 * location so one exchange's accounts query in sequence, with the family's active cap deciding how
 * many locations run at once — the shape the old `awaitGroupedExecution(..., 2)` produced by hand.
 * A flat lane cap could not express it: two slots would happily go to the same exchange.
 */
export const EXCHANGE_EVENTS_LANE_PREFIX: LaneFamily = 'exchange-events:';

/**
 * Family prefix for the per-chain account-addition lanes (`accounts-add:<chain>`). Capped at 2 per
 * chain, which is the parallelism `addMultipleAccounts` used to apply itself with
 * `awaitParallelExecution(..., 2)` — per chain, because that limiter wrapped a per-chain call. A
 * flat lane would serialize additions across chains instead, which is not what it replaced.
 */
export const ACCOUNTS_ADD_LANE_PREFIX: LaneFamily = 'accounts-add:';

/** Push live step progress for a running activity. Pure no-op-safe; calling after the spec
 *  settles is harmless (ignored by the orchestrator). */
export type ReportProgress = (steps: ActivitySteps) => void;

/**
 * Scheduling priority within a lane. Higher wins when a lane slot frees and several queued
 * activities are eligible; equal priorities fall back to insertion order (FIFO). Tag
 * user-initiated work {@link Priority.USER} so it jumps queued background work.
 */
export const Priority = {
  BACKGROUND: 0,
  NORMAL: 1,
  USER: 2,
} as const;

export type Priority = (typeof Priority)[keyof typeof Priority];

export const DEFAULT_PRIORITY: Priority = Priority.NORMAL;

/**
 * "Work matching this selector completing makes me stale." `parts` narrows the match to a specific
 * activity — matching is by id prefix on a separator boundary, the same rule
 * {@link cancelByPrefix} uses — so a producer's parameters discriminate the edge without any
 * predicate: `{ kind: PURGE, parts: ['transactions'] }` fires for `purge:transactions` and not for
 * `purge:module:aave`. Omitting `parts` matches every activity of the kind.
 */
export interface StaleAfterEdge {
  readonly kind: ActivityKind;
  readonly parts?: readonly (string | number)[];
}

/**
 * Everything the orchestrator needs to run, track, cancel and label one unit of work. A
 * producer builds a spec and hands it to {@link createTaskOrchestrator}'s `submit`. The work
 * itself stays in the producer; the orchestrator owns scheduling/lifecycle/cancellation.
 */
export interface ActivitySpec<T = unknown> {
  readonly id: ActivityId;
  readonly kind: ActivityKind;
  /** i18n, human readable. */
  readonly title: string;
  /** See {@link ActivityText}: a formatted value, or a key resolved where it is rendered. */
  readonly subtitle?: ActivityText;
  /** Optional cancellable batch (issue #10955). */
  readonly group?: GroupId;
  /** Defaults to {@link DEFAULT_LANE}. */
  readonly lane?: Lane;
  /** Scheduling priority within the lane; defaults to {@link DEFAULT_PRIORITY}. */
  readonly priority?: Priority;
  /** Must all be terminal before this activity becomes eligible to start. */
  readonly deps?: readonly ActivityId[];
  /**
   * The activity this one is a part of. Lets the whole tree be read off the specs, so a producer
   * that submits its work up front is inspectable before any of it runs — and gates one thing: a
   * child never starts before its parent has. Ordering *within* a parent is still {@link deps} and
   * the lane caps; this only stops a queued tree from running bottom-up.
   */
  readonly parent?: ActivityId;
  /**
   * Declares what invalidates this activity's data. When any matching activity *completes*, this
   * one's freshness is dropped, so `everCompleted` reads false and the next guarded fetch is
   * admitted. Nothing is re-run: the orchestrator only marks, the view decides — work nobody is
   * watching stays asleep.
   *
   * The dependency is declared by the *consumer*, so a producer never imports the modules that
   * happen to derive from it, and the causal graph is inspectable from the specs themselves.
   */
  readonly staleAfter?: readonly StaleAfterEdge[];
  /** Whether the controller may re-run it once terminal (default false). */
  readonly rerunnable?: boolean;
  /**
   * Runs the work. Returns a {@link ResultAsync} so failures are values, not throws — the
   * producer wraps `runTask` via `fromTaskResult`. `report` pushes optional step progress.
   */
  readonly run: (report: ReportProgress) => ResultAsync<T, TaskError>;
  /** Aborts in-flight work (request/task). Absent ⇒ the activity is not cancellable while
   *  running (queued cancellation still works). */
  readonly cancel?: () => void;
  /**
   * Tear down side resources the producer set up for this activity (a poll interval, a
   * subscription). Run once when the activity settles — on completion, failure, cancel-while-running
   * *and* cancel-while-queued (where `run` never executes) — so producers don't need a `try/finally`
   * around `submitTask`. Re-armed on re-run.
   */
  readonly cleanup?: () => void;
  readonly retry?: RetryOptions;
  readonly timeoutMs?: number;
  /**
   * Run this work through the orchestrator but keep it out of the task-center render model. The
   * spine still schedules, tracks, cancels and cleans it up as usual; only the reactive
   * projection drops it (see {@link ../../use-task-orchestrator}). For unlock-time work (login,
   * account creation) that must not leave a stale entry once the shell mounts.
   */
  readonly ephemeral?: boolean;
  /**
   * Marks work that deletes data before re-deriving it, so the eligibility rules can keep it from
   * overlapping work that writes to the same rows. Everything else may overlap harmlessly — the
   * backend serialises writes, matching holds its own locks and decoding is idempotent — so this
   * is the one exclusion worth expressing. Declared by a flow via `HistoryFlow.resets`.
   */
  readonly resets?: boolean;
}

/** Per-lane concurrency caps; lanes not listed use the default cap. */
export type LaneCaps = Partial<Readonly<Record<Lane, number>>>;

/**
 * Caps for *families* of lanes, keyed by id prefix. Producers that mint a lane per entity — one per
 * chain, say — cannot enumerate their lane names up front, so an exact-name cap can never reach
 * them and they would all silently take the default. A family caps every lane whose name starts
 * with the prefix, each lane still holding its own independent slots.
 *
 * Resolution order is exact name, then the longest matching prefix, then the default cap.
 */
export type LaneFamilyCaps = Partial<Readonly<Record<LaneFamily, number>>>;

/**
 * How many *distinct lanes* within a family may run at once, keyed by the same id prefix as
 * {@link LaneFamilyCaps}. Where a family cap bounds work *within* each lane, this bounds how many
 * lanes are live at all.
 *
 * Needed once a producer submits its whole tree up front rather than fanning out as it runs: with
 * every per-entity activity queued from the start, a per-lane cap alone would let every entity
 * progress at once — two accounts on each of ten chains is twenty concurrent requests. Capping
 * active lanes restores the nesting that submitting lazily used to provide, so the *shape* is
 * `active lanes × per-lane cap` rather than a flat total.
 */
export type LaneFamilyActiveCaps = Partial<Readonly<Record<LaneFamily, number>>>;
