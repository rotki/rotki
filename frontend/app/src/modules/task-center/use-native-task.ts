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
 * Carries `run`'s return value rather than discarding it. Producers used to smuggle their result
 * out through a variable in the enclosing closure, which is only correct when `run` actually
 * executes — and a re-entrant call for a live id shares the in-flight promise *without* running,
 * so the second caller read the local's initial value (`false`, `undefined`, `-1`) and treated it
 * as a successful result. Returning the value means every awaiter, deduped or not, gets the same
 * real one.
 *
 * This is sound only because a shared id means shared work: two calls that would produce
 * different results must not collide on one id in the first place.
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
 * What the orchestrator hands a running activity: its progress sink and its own task runner.
 * Passing the runner explicitly (rather than reading an ambient "current activity") keeps the
 * binding correct for producers that await before submitting their backend task.
 */
export interface ActivityContext {
  readonly report: ReportProgress;
  readonly runTask: RunBackendTask;
}

/**
 * A producer-facing {@link ActivitySpec}: `run` takes an {@link ActivityContext}, and there is no
 * `cancel` — cancellation is the orchestrator's job now that it knows the backend task id.
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
   * ⚠️ KNOWN: this resolves a tick BEFORE the activity is marked terminal. It settles from the
   * producer's own promise, while the orchestrator writes the status in `settleTerminal` a tick
   * later — so **do not read `statusOf`/`useWorkStatus` for an activity you just awaited**:
   *
   *     await submitTask({ id, ... });
   *     statusOf(kind).active;    // still true — NOT settled yet
   *
   * Reactive readers are fine (they re-render on the next emit); this only bites an imperative
   * read in the same tick, and it fails silently. Today every such read in the app is an entry
   * guard, so nothing is broken — the hazard is new code. If you need the settled status, flush a
   * microtask first (specs use `flushPromises()`).
   *
   * Three attempts to close the gap all broke re-login deterministically
   * (`tests/e2e/specs/settings/rpc.spec.ts:36` hangs with the unlock form disabled) while the unit
   * suite stayed fully green — resolving from `orchestrator.onChange`, an `onSettled` hook fired
   * inside `settleTerminal`, and either of those plus a dedicated session lane. Root cause is not
   * yet known; every attempt so far reasoned from unit tests, which do not reproduce it. Diagnose
   * from the browser before trying a fourth.
   */
  readonly submitTask: <T = void>(spec: NativeActivitySpec<T>) => Promise<TaskOutcome<T>>;
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

  function cancelActivity(kind: ActivityKind, ...parts: (string | number)[]): void {
    // The Result is deliberately dropped: "nothing to cancel" (unknown id / already terminal) is
    // the normal case at a supersede site, not an error the caller can act on.
    orchestrator.cancel(makeActivityId(kind, ...parts));
  }

  // Not `async`: re-entrant calls must return the *same* in-flight promise (identity dedup), and
  // the body owns its own deferred — wrapping it in async would create a fresh promise per call.
  // eslint-disable-next-line @typescript-eslint/promise-function-async
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
      settle(outcome);
    }

    // The backend task this activity is currently driving, captured as `run` spawns it. Reset on
    // every run so a re-run cancels its own task, not the previous attempt's.
    let backendTaskId: number | undefined;

    // What names the task in the monitor's failure notification and the dev logs. The activity
    // already carries both halves, so a producer never writes this string twice.
    // `resolveText` because a subtitle may be a key+params pair rather than a string; the label
    // is a one-shot log/notification string, so resolving it here at submit time is correct.
    const subtitle = resolveText(t, spec.subtitle);
    const label = subtitle ? `${spec.title} (${subtitle})` : spec.title;

    async function runTask<R>(task: () => Promise<{ taskId: number }>): Promise<Result<R, TaskError>> {
      return runBackendTask<R>(async () => {
        const pending = await task();
        backendTaskId = pending.taskId;
        return pending;
      }, label);
    }

    // Cancelling the activity aborts whatever backend task it spawned. Producers no longer pass a
    // cancel handle: an activity that never started one still settles CANCELLED (the orchestrator
    // does that), this just stops the work on the backend.
    function cancel(): void {
      if (backendTaskId !== undefined)
        startPromise(cancelTaskById(backendTaskId));
    }

    // The spec's run carries the real outcome (and its store side effects); tee it so the caller
    // awaits the work itself, not just a status flip.
    async function run(report: ReportProgress): Promise<Result<T, TaskError>> {
      backendTaskId = undefined;
      const outcome = spec.run({ report, runTask });
      outcome.then(finish, (error: unknown) => finish(err(TaskFailed({ message: getErrorMessage(error) }))));
      return outcome;
    }

    // An activity cancelled while still queued never calls `run`; resolve it from the snapshot so
    // the caller's await never hangs.
    stop = orchestrator.onChange(() => {
      const activity = orchestrator.snapshot().find(item => item.id === spec.id);
      if (activity && isTerminalStatus(activity.status))
        finish(err(Cancelled({ message: 'Cancelled before running' })));
    });

    // Stored erased, handed back at this spec's own value type. The return below needs no
    // assertion — `never` is assignable to every `T` — so this is the single unsound step, and it
    // is why the map is keyed to `never` rather than `unknown`.
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- a per-entry key/value type correlation TypeScript cannot express without existential types; contained to this line
    inflight.set(spec.id, promise as Promise<TaskOutcome<never>>);
    orchestrator.submit({ ...spec, cancel, run });
    return promise;
  }

  return {
    cancelActivity,
    cancelByKind,
    cancelByPrefix,
    reportProgress,
    statusOf,
    submitTask,
    useIsActive,
    useWorkStatus,
  };
});
