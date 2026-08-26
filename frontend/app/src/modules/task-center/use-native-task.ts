import type { ResultAsync } from 'plainfp/result-async';
import type { ComputedRef } from 'vue';
import type { ActivitySpec, ReportProgress } from './core/orchestrator/spec';
import { startPromise } from '@shared/utils';
import { err, type Result } from 'plainfp/result';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { isTerminalStatus } from './core/status';
import {
  type ActivityId,
  type ActivityKind,
  type ActivitySteps,
  makeActivityId,
  resolveText,
  type WorkStatus,
} from './core/types';
import { useTaskOrchestrator } from './use-task-orchestrator';

// Re-exported so a migrating producer pulls the submission bridge, the id helpers and the
// outcome guard from one module, keeping its import count under the `@rotki/max-dependencies` cap.
export { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from './core/types';

export { isActionable } from '@/modules/core/tasks/task-result';

/**
 * Outcome of a native activity: the work's side effects landed, success or failure as a value.
 *
 * Carries `run`'s return value so every awaiter, deduped or not, gets the same one. A result
 * smuggled out through a closure variable instead is wrong for a re-entrant call, which shares the
 * in-flight promise *without* running and so reads the local's initial value.
 *
 * Sound only because a shared id means shared work: two calls that would produce different
 * results must not collide on one id.
 */
export type TaskOutcome<T = void> = Result<T, TaskError>;

/**
 * Runs a backend task *as part of the activity that received it*: it records the backend task id
 * the call spawned, which is what lets the orchestrator abort that task on cancel, and it labels
 * the task from the activity's own title/subtitle. Producers get it from their
 * {@link ActivityContext} and never reach for the unbound runner.
 */
export type RunBackendTask = <R>(task: () => Promise<{ taskId: number }>) => Promise<Result<R, TaskError>>;

/**
 * What the orchestrator hands a running activity: its progress sink, its own task runner, and
 * whether it has since been cancelled.
 * Passing the runner explicitly (rather than reading an ambient "current activity") keeps the
 * binding correct for producers that await before submitting their backend task.
 */
export interface ActivityContext {
  readonly report: ReportProgress;
  readonly runTask: RunBackendTask;
  /**
   * True once this activity has been cancelled — **a body with more than one stage must check it
   * between them**.
   *
   * Cancelling settles the *record*; it cannot interrupt a running async body. A multi-stage
   * producer that does not read this runs to completion after the row already says CANCELLED,
   * writing results and recording a completion for work the user stopped.
   */
  readonly cancelled: () => boolean;
}

/**
 * A producer-facing {@link ActivitySpec}: `run` takes an {@link ActivityContext}, and there is no
 * `cancel`, because the orchestrator holds the backend task id and cancels on the producer's
 * behalf.
 */
export type NativeActivitySpec<T = void> = Omit<ActivitySpec<T>, 'cancel' | 'run'> & {
  readonly run: (ctx: ActivityContext) => ResultAsync<T, TaskError>;
};

interface UseNativeTaskReturn {
  /**
   * Submit a producer's work to the orchestrator and await its terminal outcome. The producer
   * keeps its async API (`Promise<void>`-shaped callers still `await` the data); the orchestrator
   * gains ownership of queueing, lane caps, cancellation and re-run. Re-entrant calls for the same
   * {@link ActivityId} share the in-flight promise instead of double-submitting.
   *
   * Resolves a tick BEFORE the activity is marked terminal, so an imperative
   * `statusOf`/`useWorkStatus` read right after an `await` still reports active, silently. Reactive
   * readers are unaffected. Flush a microtask first if you need the settled status.
   */
  readonly submitTask: <T = void>(spec: NativeActivitySpec<T>) => Promise<TaskOutcome<T>>;
  /**
   * Like {@link submitTask}, but replaces the run already in flight for this id rather than joining
   * it. For user-initiated work, which must not be handed a background run's parameters.
   */
  readonly supersedeTask: <T = void>(spec: NativeActivitySpec<T>) => Promise<TaskOutcome<T>>;
  /**
   * Settle and drop every in-flight submission. Called when a session ends, so no id survives into
   * the next one — `submitTask` dedups by id, and a surviving id hands the next session a promise
   * that can never resolve.
   */
  readonly reset: () => void;
  /**
   * Cancel one activity by identity — `orchestrator.cancel(makeActivityId(kind, ...parts))`. The
   * replacement for the old imperative cancel-by-task-type at producer call sites: it settles the
   * activity terminal *immediately* (so awaiting readers and `useWorkStatus` spinners unblock even
   * when the backend refuses the abort) and fires the spec's own cancel handle for the backend.
   * Cancelling an unknown or already-terminal activity is a no-op.
   */
  readonly cancelActivity: (kind: ActivityKind, ...parts: (string | number)[]) => void;
  /**
   * Cancel every in-flight activity under `kind:parts`. For the sites that cancelled a whole
   * whole category of work while the producer gives each request its own id (historic prices, tx
   * lookups), where {@link cancelActivity}'s exact id would never match.
   */
  readonly cancelByPrefix: (kind: ActivityKind, ...parts: (string | number)[]) => void;
  /**
   * Cancel every in-flight activity of a kind, whatever its id shape. For the sites that cancelled
   * a whole kind whose producers submit under several id shapes at once (tx decoding runs
   * `tx_decoding:<chain>` and `tx_decoding:<chain>:pull`).
   */
  readonly cancelByKind: (kind: ActivityKind) => void;
  /**
   * Push step progress onto a running native activity by id. For producers that poll their own
   * progress (rather than receiving it inside `run`); delegated to the orchestrator, no-op unless
   * the activity is running.
   */
  readonly reportProgress: (id: ActivityId, steps: ActivitySteps) => void;
  /**
   * Synchronous {@link WorkStatus} snapshot for a kind (or specific id) — the imperative sibling
   * of `useWorkStatus`. For producer-side guards that need to check liveness *before* submitting
   * (e.g. "is one already running?") rather than reactively. Delegated to the orchestrator.
   */
  readonly statusOf: (kind: ActivityKind, ...parts: (string | number)[]) => WorkStatus;
  /**
   * Reactive {@link WorkStatus} for a kind (or specific id) — the sibling of {@link statusOf} for
   * producers that also read their own liveness. Delegated to the orchestrator, the same seam
   * `useTaskCenter` exposes; here so a producer needing both stays under the import cap.
   */
  readonly useWorkStatus: (kind: ActivityKind, ...parts: (string | number)[]) => ComputedRef<WorkStatus>;
  /** Liveness only — the one-field read most spinners want. */
  readonly useIsActive: (kind: ActivityKind, ...parts: (string | number)[]) => ComputedRef<boolean>;
}

/**
 * The single per-producer bridge that turns a {@link ActivitySpec} into an awaitable. Used by
 * each producer as it migrates native (Phase 2), so the migration is a thin call-site change and
 * the await semantics callers depend on are preserved.
 */
export const useNativeTask = createSharedComposable((): UseNativeTaskReturn => {
  const { t } = useI18n({ useScope: 'global' });
  const orchestrator = useTaskOrchestrator();
  const { cancelByKind, cancelByPrefix, reportProgress, statusOf, useIsActive, useWorkStatus } = orchestrator;
  const { cancelTaskById, runTask: runBackendTask } = useTaskHandler();
  /**
   * The promise handed back to a re-entrant caller. Its value type is the submitting spec's `T`,
   * which this map cannot express across heterogeneous ids — the erasure is contained here and
   * re-applied at the one return below, rather than leaking `any` into producer call sites.
   */
  const inflight = new Map<ActivityId, Promise<TaskOutcome<never>>>();

  /**
   * How to settle each in-flight submission from the outside. Held beside {@link inflight} because
   * the promise alone cannot be resolved by anyone but its own closure, and a session ending must
   * be able to settle every caller it is about to abandon.
   */
  const inflightFinish = new Map<ActivityId, (outcome: TaskOutcome<never>) => void>();

  /**
   * How to tell each in-flight submission that it has been cancelled, so a multi-stage body can
   * stop between stages. Kept beside {@link inflight} for the same reason: a session ending has to
   * reach bodies it is about to abandon, and settling the caller does not stop the body.
   */
  const inflightCancel = new Map<ActivityId, () => void>();

  /**
   * Drop every in-flight submission, settling its callers first.
   *
   * Must run when a session ends. The map is app-scoped and `submitTask` dedups on id identity,
   * so an id left behind hands the *next* session's caller a promise from a session that is gone
   * and can never resolve.
   *
   * Settled as cancelled rather than merely cleared: an abandoned caller is still awaiting this
   * promise, so dropping the reference alone would suspend it forever.
   *
   * Cancel runs before the settle, so a body checking `cancelled()` between stages sees the
   * session end instead of carrying on with work for a user who has logged out.
   */
  function reset(): void {
    for (const requestCancel of inflightCancel.values())
      requestCancel();

    for (const finishInflight of inflightFinish.values())
      finishInflight(err(Cancelled({ message: 'session ended' })));

    inflight.clear();
    inflightFinish.clear();
    inflightCancel.clear();
  }

  /**
   * Replace the run already in flight for this id, instead of joining it.
   *
   * {@link submitTask} dedups: a second caller for a live id is handed the first run's promise
   * and the first run's *parameters*. That is right for background work — two periodic ticks should
   * share one run — and wrong for a user, who asked for fresh data and would silently receive
   * whatever the background run happened to be doing.
   *
   * Cancelling settles the record immediately, so this does not wait on the aborted work itself.
   * The `await` is defensive: settling is synchronous today, but if it ever becomes async,
   * submitting without it would dedup the replacement onto the corpse.
   *
   * `cancel`'s Result is dropped on purpose: "nothing to cancel", whether already terminal or gone
   * between the lookup and the call, is the normal race here rather than something a caller acts on.
   */
  async function supersedeTask<T = void>(spec: NativeActivitySpec<T>): Promise<TaskOutcome<T>> {
    const running = inflight.get(spec.id);
    if (running) {
      orchestrator.cancel(spec.id);
      await running;
    }

    return submitTask(spec);
  }

  /**
   * Cancel one activity by id, if it is still running.
   *
   * @remarks
   * The Result is dropped on purpose: an unknown or already-terminal id is the normal case at a
   * supersede site, not an error a caller can act on.
   */
  function cancelActivity(kind: ActivityKind, ...parts: (string | number)[]): void {
    orchestrator.cancel(makeActivityId(kind, ...parts));
  }

  /**
   * Submit an activity, or join the one already running under this id.
   *
   * @remarks
   * Deliberately not `async`. Re-entrant callers must receive the *same* in-flight promise for
   * dedup to hold, and the body owns its own deferred; an `async` wrapper would mint a fresh
   * promise per call and every caller would get its own.
   */
  // eslint-disable-next-line @typescript-eslint/promise-function-async -- returns the shared in-flight promise by identity, see above
  function submitTask<T = void>(spec: NativeActivitySpec<T>): Promise<TaskOutcome<T>> {
    const running = inflight.get(spec.id);
    if (running)
      return running;

    let settled = false;
    let settle: (outcome: TaskOutcome<T>) => void = () => {};
    let stop: () => void = () => {};

    const promise = new Promise<TaskOutcome<T>>((resolve) => {
      settle = resolve;
    });

    function finish(outcome: TaskOutcome<T>): void {
      if (settled)
        return;
      settled = true;
      stop();
      inflight.delete(spec.id);
      inflightFinish.delete(spec.id);
      inflightCancel.delete(spec.id);
      settle(outcome);
    }

    /**
     * The backend task this activity is currently driving, captured as `runTask` spawns it.
     * Cleared at the top of every run, so a re-run aborts its own task rather than the previous
     * attempt's already-finished one.
     */
    let backendTaskId: number | undefined;

    const subtitle = resolveText(t, spec.subtitle);
    const label = subtitle ? `${spec.title} (${subtitle})` : spec.title;

    async function runTask<R>(task: () => Promise<{ taskId: number }>): Promise<Result<R, TaskError>> {
      return runBackendTask<R>(async () => {
        const pending = await task();
        backendTaskId = pending.taskId;
        return pending;
      }, label);
    }

    /** Set once this activity is cancelled; read by the body through `ctx.cancelled()`. */
    let cancelRequested = false;

    function requestCancel(): void {
      cancelRequested = true;
    }

    /**
     * Aborts the backend task, which is not the same as stopping the body: a body between stages
     * has spawned no task yet, so there is nothing to abort and only `cancelled()` reaches it.
     */
    function cancel(): void {
      requestCancel();
      if (backendTaskId !== undefined)
        startPromise(cancelTaskById(backendTaskId));
    }

    /**
     * @returns the spec's own promise, not a derived one. It carries the real outcome and the
     * store side effects, so the caller awaits the work itself rather than a status flip.
     */
    async function run(report: ReportProgress): Promise<Result<T, TaskError>> {
      backendTaskId = undefined;
      const outcome = spec.run({ cancelled: () => cancelRequested, report, runTask });
      outcome.then(finish, (error: unknown) => finish(err(TaskFailed({ message: getErrorMessage(error) }))));
      return outcome;
    }

    stop = orchestrator.onChange(() => {
      const activity = orchestrator.snapshot().find(item => item.id === spec.id);
      if (activity && isTerminalStatus(activity.status))
        finish(err(Cancelled({ message: 'Cancelled before running' })));
    });

    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- a per-entry key/value type correlation TypeScript cannot express without existential types; the map is keyed to `never` so only this line is unsound, the read back needs no assertion
    inflight.set(spec.id, promise as Promise<TaskOutcome<never>>);
    inflightFinish.set(spec.id, finish);
    inflightCancel.set(spec.id, requestCancel);
    orchestrator.submit({ ...spec, cancel, run });
    return promise;
  }

  return {
    cancelActivity,
    cancelByKind,
    cancelByPrefix,
    reportProgress,
    statusOf,
    reset,
    submitTask,
    supersedeTask,
    useIsActive,
    useWorkStatus,
  };
});
