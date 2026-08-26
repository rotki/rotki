import { err, isErr, ok, type Result } from 'plainfp/result';
import { hasTag, tag } from 'plainfp/tagged';

/**
 * The task layer's outcome model: a task runs as a value, so every way it can end is a tag on
 * {@link TaskError} rather than a branch on a union. This lives in the task layer (not in any
 * feature) because it describes task outcomes, and the orchestrator / producers consume it
 * without the task layer ever depending on them.
 *
 * @packageDocumentation
 */

/** User explicitly cancelled the task. */
export const Cancelled = tag('Cancelled');

/** Backend reported the task as cancelled. */
export const BackendCancelled = tag('BackendCancelled');

/**
 * The work was deliberately not run because the user configured it off (a disabled chain, an
 * inactive module). Terminal and explainable: `message` is the user-facing reason ("disabled in
 * settings"), which the task center renders on the row.
 *
 * Not the `Skipped` tag removed in `6e128fcaa5`. That one meant "a duplicate was already in
 * flight" — an artefact of the dedup guard, invisible to users. This is a user-facing outcome.
 */
export const Skipped = tag('Skipped');

/** An actual, actionable failure the consumer should surface. */
export const TaskFailed = tag('TaskFailed');

export type TaskError =
  | ReturnType<typeof Cancelled<{ message: string }>>
  | ReturnType<typeof BackendCancelled<{ message: string }>>
  | ReturnType<typeof Skipped<{ message: string }>>
  | ReturnType<typeof TaskFailed<{ message: string; cause?: unknown }>>;

/** True when the error is any flavour of cancellation (user or backend). */
export function isCancellation(error: TaskError): boolean {
  return hasTag(error, 'Cancelled') || hasTag(error, 'BackendCancelled');
}

/**
 * True when the error is an actionable failure rather than a cancellation. A type predicate, so a
 * caller that needs the underlying `cause` (e.g. to pull field-level validation errors off an
 * `ApiValidationError`) gets it without a cast.
 */
export function isActionable(error: TaskError): error is Extract<TaskError, { _tag: 'TaskFailed' }> {
  return hasTag(error, 'TaskFailed');
}

/**
 * The `Error` a form-facing caller should report for a failure. The original `cause` is returned
 * as-is when it is an `Error`, so a caller that branches on `ApiValidationError` to fill in
 * per-field errors still gets it; wrapping the message in a bare `Error` would flatten every
 * validation failure into one generic toast.
 *
 * Returned rather than thrown: producers report failures as values now, so the caller is not
 * inside a `try` that a throw could unwind to.
 */
export function errorOf(error: TaskError): Error {
  if (isActionable(error) && error.cause instanceof Error)
    return error.cause;

  return new Error(error.message);
}

/**
 * Fold a fan-out's child outcomes into the one verdict its parent should settle on.
 *
 * A parent must not claim a success its children did not earn. The shape this exists to kill is
 * `await Promise.all(children); return ok(undefined)`, which completes even when every child
 * failed — and where the parent's completion-ledger entry is load-bearing, that writes "we have
 * data" over nothing at all. Concretely: backend unreachable on the first history sync, every
 * account fails, the umbrella completes anyway, `everCompleted` goes true and every later
 * non-user-initiated refresh short-circuits on it, so history silently never syncs again.
 *
 * One success is enough. A fan-out is partial by nature — one chain failing is that chain's
 * failure, not the refresh's — so this reports a failure only when *nothing* got through. An empty
 * batch is `Skipped`: no work ran, so no work succeeded, and a parent that ran nothing must not
 * record a completion either.
 *
 * The losing errors are dropped rather than merged. Each child has already surfaced its own
 * failure where it happened; this only has to pick the most actionable one for the parent's row,
 * which is why an actionable failure outranks a cancellation and a cancellation outranks a skip.
 */
export function combineOutcomes(outcomes: readonly Result<unknown, TaskError>[]): Result<void, TaskError> {
  const errors: TaskError[] = [];
  for (const outcome of outcomes) {
    if (!isErr(outcome))
      return ok(undefined);
    errors.push(outcome.error);
  }

  const failure = errors.find(error => isActionable(error))
    ?? errors.find(error => isCancellation(error))
    ?? errors.at(0);

  return err(failure ?? Skipped({ message: 'nothing ran' }));
}

/**
 * Run `handler` only when `outcome` is an actionable failure, not a cancellation. The canonical
 * tail for a native producer that surfaces real errors (notify, throw, …) while staying silent
 * on cancels. No-op on success.
 */
export function onActionableError(outcome: Result<unknown, TaskError>, handler: (error: TaskError) => void): void {
  if (isErr(outcome) && isActionable(outcome.error))
    handler(outcome.error);
}
