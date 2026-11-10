import { checkIfDevelopment } from '@shared/utils';
import { err, ok, type Result } from 'plainfp/result';
import { FailureCause, parseFailureCause } from '@/modules/core/api/failure-cause';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { createStatusError } from '@/modules/core/api/response-handlers';
import { HTTPStatus } from '@/modules/core/api/types/http';
import { logger } from '@/modules/core/common/logging/logging';
import { onSessionEnd } from '@/modules/core/session/session-lifecycle';
import {
  BackendCancelled,
  Cancelled,
  type TaskError,
  TaskFailed,
} from '@/modules/core/tasks/task-result';
import { type CompletedTaskOutcome, type RunTaskOptions, TaskNotFoundError } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

export type { TaskError } from '@/modules/core/tasks/task-result';

const USER_CANCELLED_TASK = 'task_cancelled_by_user';

interface TaskActionResult<T> extends CompletedTaskOutcome<T> {
  error?: any;
}

/**
 * Reads the outcome of a task the backend gave a cause for, which makes it a failure whatever result
 * it carries.
 *
 * @remarks
 * A few endpoints answer a failure with `false` and the reason, and the PnL report with the id of
 * the report it stopped on. A task opts out with `conflictIsResult` for a 409, since asset updates
 * answer one with conflicts to resolve.
 */
function readFailedOutcome<R>(
  { cause, message, result, statusCode }: TaskActionResult<R>,
  options: RunTaskOptions,
  describeTask: () => string,
): Result<R, TaskError> {
  const failureCause = parseFailureCause(cause);

  if (failureCause === FailureCause.CANCELLED)
    return err(BackendCancelled({ message: `Backend cancelled ${describeTask()}` }));

  if (options.conflictIsResult === true && statusCode === HTTPStatus.CONFLICT)
    return ok(result);

  return failedOutcome({ message, result, statusCode }, failureCause);
}

/** Preserve a completed task's HTTP failure status for consumers that distinguish conflicts. */
function failedOutcome({ message, statusCode }: TaskActionResult<unknown>, failureCause?: FailureCause): Result<never, TaskError> {
  const cause = statusCode !== undefined && statusCode >= HTTPStatus.BAD_REQUEST
    ? createStatusError(statusCode, message)
    : undefined;
  return err(TaskFailed({ cause, failureCause, message }));
}

function useTaskHandlerInternal(): {
  runTask: <R>(task: () => Promise<{ taskId: number }>, label: string, options?: RunTaskOptions) => Promise<Result<R, TaskError>>;
  cancelTaskById: (taskId: number) => Promise<boolean>;
  handleResult: (result: TaskActionResult<any>, taskId: number) => void;
} {
  /**
   * The resolver waiting on each in-flight backend task, keyed by that task's backend id.
   *
   * @remarks
   * The id is the only identity the backend reports back with a result. Keying by task *type*
   * instead let two concurrent tasks of one type overwrite each other's entry, so the loser's
   * promise was never settled and whatever awaited it hung for the rest of the session.
   */
  const handlers = new Map<number, (result: TaskActionResult<any>) => void>();
  const store = useTaskStore();
  const api = useTaskApi();

  /** Hand a completed backend result to the promise waiting on it, and drop the task. */
  function handleResult(result: TaskActionResult<any>, taskId: number): void {
    const handler = handlers.get(taskId);

    if (handler)
      handler(result);
    /* c8 ignore next 3 */
    else
      logger.warn(`missing handler for task ${taskId}`);

    store.remove(taskId);
  }

  /**
   * Run a backend task and get its outcome as a value. Every way the task can end is a tag on
   * {@link TaskError}: the caller never branches on a success flag. `label` names the task in the
   * monitor's failure notification and in the dev logs; the orchestrator builds it from the
   * activity that owns the run, so it carries the instance (address, asset, xpub) too.
   */
  async function runTask<R>(
    task: () => Promise<{ taskId: number }>,
    label: string,
    options: RunTaskOptions = {},
  ): Promise<Result<R, TaskError>> {
    let taskId: number;
    try {
      ({ taskId } = await task());
    }
    catch (error: unknown) {
      if (isRequestCancellation(error))
        return err(Cancelled({ message: 'Request cancelled' }));
      throw error;
    }

    store.addTask(taskId, label);

    return new Promise<Result<R, TaskError>>((resolve) => {
      handlers.set(taskId, (outcome) => {
        const { cause, error, message, result } = outcome;
        const describeTask = (): string => `task_id: ${taskId}, task: ${label}`;
        handlers.delete(taskId);

        if (error) {
          resolve(err(TaskFailed({ cause: error, message: error.message ?? '' })));
        }
        else if (cause !== undefined) {
          resolve(readFailedOutcome(outcome, options, describeTask));
        }
        else if (result !== null) {
          resolve(ok(result));
        }
        else if (message === USER_CANCELLED_TASK) {
          if (checkIfDevelopment() && !import.meta.env.VITE_TEST)
            logger.debug(`Request cancelled -> task_id: ${taskId}, task: ${label}`);

          resolve(err(Cancelled({ message: 'Request cancelled' })));
        }
        else if (message) {
          resolve(failedOutcome(outcome));
        }
        else {
          resolve(err(BackendCancelled({ message: `Backend cancelled ${describeTask()}` })));
        }
      });
    });
  }

  /**
   * Settle every task still awaited as cancelled.
   *
   * @remarks
   * Runs when the session ends. The backend logout cancels its tasks and forgets their results, so
   * a task left here would never be reported and whatever awaits it would stay suspended.
   */
  function settleAll(): void {
    for (const handler of handlers.values())
      handler({ message: USER_CANCELLED_TASK, result: null });
  }

  onSessionEnd('task-handlers', settleAll);

  /**
   * Abort one backend task by its id. The entry point for the orchestrator, whose activities know
   * the task they spawned but not the `Task` record. `handlers` is the truthful liveness check:
   * it is what an in-flight promise hangs off, so an unknown (already settled) id is a no-op.
   */
  async function cancelTaskById(taskId: number): Promise<boolean> {
    if (!handlers.has(taskId))
      return false;

    try {
      const deleted = await api.cancelAsyncTask(taskId);

      if (deleted) {
        store.lock(taskId);
        handleResult({ message: USER_CANCELLED_TASK, result: null }, taskId);
        store.unlock(taskId);
      }

      return deleted;
    }
    catch (error_: any) {
      if (error_ instanceof TaskNotFoundError)
        store.remove(taskId);

      return false;
    }
  }

  return {
    cancelTaskById,
    handleResult,
    runTask,
  };
}

export const useTaskHandler = createSharedComposable(useTaskHandlerInternal);
