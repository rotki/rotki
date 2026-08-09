import type { ActivitySpec, ReportProgress } from './spec';
import { err, type Result } from 'plainfp/result';
import { type ResultAsync, retry, timeout } from 'plainfp/result-async';
import { hasTag } from 'plainfp/tagged';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { isTerminalStatus } from '../status';
import { type ActivityId, type ActivityStatus, ActivityStatus as Status } from '../types';

/**
 * How a single activity runs and how its outcome becomes a status. Pure and orchestrator-agnostic,
 * like {@link ./projection}: nothing here reads or writes orchestrator state, which keeps the
 * orchestrator module about scheduling, control and the record map.
 */

/** The subset of a record these helpers need — structurally satisfied by `ActivityRecord`. */
export interface LifecycleRecord {
  readonly status: ActivityStatus;
  readonly spec: { readonly parent?: ActivityId };
}

/**
 * Terminal, but not a success — CANCELLED, FAILED or SKIPPED.
 *
 * The distinction the subtree cascade turns on: an activity that ends this way takes its children
 * with it, while a COMPLETE one leaves them alone.
 */
export function endedIncomplete(record: LifecycleRecord): boolean {
  return isTerminalStatus(record.status) && record.status !== Status.COMPLETE;
}

/** The live direct children of `id`, in insertion order. */
export function liveChildrenOf<T extends LifecycleRecord>(
  records: ReadonlyMap<ActivityId, T>,
  id: ActivityId,
): T[] {
  const children: T[] = [];
  for (const record of records.values()) {
    if (record.spec.parent === id && !isTerminalStatus(record.status))
      children.push(record);
  }
  return children;
}

/**
 * Which terminal status an outcome lands on.
 *
 * `cancelRequested` wins over everything: a cancelled activity stays CANCELLED even when the work
 * it was aborting goes on to settle `ok`, which is what lets a parent be cancelled while its own
 * body is still resolving.
 */
export function terminalStatus(cancelRequested: boolean, outcome: Result<unknown, TaskError>): ActivityStatus {
  if (cancelRequested)
    return Status.CANCELLED;
  if (outcome.ok)
    return Status.COMPLETE;

  const { error } = outcome;
  if (hasTag(error, 'Cancelled') || hasTag(error, 'BackendCancelled'))
    return Status.CANCELLED;
  if (hasTag(error, 'Skipped'))
    return Status.SKIPPED;

  return Status.FAILED;
}

/**
 * Run a spec's body under its declared timeout and retry policy, as a value.
 *
 * ⚠️ The catch is not defensive dressing: a producer's `ResultAsync` should never reject, and one
 * that does would otherwise leave its activity RUNNING for the life of the process.
 */
export async function runActivity(
  spec: ActivitySpec,
  report: ReportProgress,
): Promise<Result<unknown, TaskError>> {
  const runOnce = async (): ResultAsync<unknown, TaskError> => {
    const base = spec.run(report);
    return spec.timeoutMs === undefined
      ? base
      : timeout(base, spec.timeoutMs, () => TaskFailed({ message: 'Timed out' }));
  };

  try {
    return await (spec.retry ? retry(runOnce, spec.retry) : runOnce());
  }
  catch (error) {
    return err(TaskFailed({ cause: error, message: 'Unexpected error' }));
  }
}
