import type { ActionResult } from '@rotki/common';
import { checkIfDevelopment } from '@shared/utils';
import { err, ok, type Result } from 'plainfp/result';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { logger } from '@/modules/core/common/logging/logging';
import {
  BackendCancelled,
  Cancelled,
  type TaskError,
  TaskFailed,
} from '@/modules/core/tasks/task-result';
import { TaskNotFoundError } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

export type { TaskError } from '@/modules/core/tasks/task-result';

const USER_CANCELLED_TASK = 'task_cancelled_by_user';

interface TaskActionResult<T> extends ActionResult<T> {
  error?: any;
}

function useTaskHandlerInternal(): {
  runTask: <R>(task: () => Promise<{ taskId: number }>, label: string) => Promise<Result<R, TaskError>>;
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
      handlers.set(taskId, ({ error, message, result }) => {
        handlers.delete(taskId);

        if (error) {
          resolve(err(TaskFailed({ cause: error, message: error.message ?? '' })));
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
          resolve(err(TaskFailed({ message })));
        }
        else {
          resolve(err(BackendCancelled({ message: `Backend cancelled task_id: ${taskId}, task: ${label}` })));
        }
      });
    });
  }

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
