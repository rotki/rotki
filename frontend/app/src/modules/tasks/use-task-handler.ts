import type { ActionResult } from '@rotki/common';
import { checkIfDevelopment } from '@shared/utils';
import { useTaskApi } from '@/composables/api/task';
import { arrayify } from '@/modules/common/data/array';
import { logger } from '@/modules/common/logging/logging';
import { TaskType } from '@/modules/tasks/task-type';
import { type Task, type TaskMeta, TaskNotFoundError } from '@/modules/tasks/types';
import { useTaskStore } from '@/modules/tasks/use-task-store';

const USER_CANCELLED_TASK = 'task_cancelled_by_user';

export interface TaskSuccess<R> {
  readonly success: true;
  readonly result: R;
  readonly message?: string;
}

export interface TaskFailure {
  readonly success: false;
  readonly message: string;
  readonly error?: unknown;
  readonly cancelled: boolean;
  readonly backendCancelled: boolean;
  readonly skipped: boolean;
}

export type TaskResult<R> = TaskSuccess<R> | TaskFailure;

/**
 * Returns true when the failure represents an actual error that the consumer should handle
 * (i.e. not a cancellation or a guard skip).
 */
export function isActionableFailure(outcome: TaskResult<unknown>): outcome is TaskFailure {
  return !outcome.success && !outcome.cancelled && !outcome.skipped;
}

export interface RunTaskOptions<M extends TaskMeta> {
  type: TaskType;
  meta: M;
  unique?: boolean;
  guard?: boolean;
}

interface TaskActionResult<T> extends ActionResult<T> {
  error?: any;
}

function makeFailure(fields: Omit<TaskFailure, 'success'>): TaskFailure {
  return { success: false, ...fields };
}

function makeSkipped(message: string): TaskFailure {
  return makeFailure({ message, cancelled: false, backendCancelled: false, skipped: true });
}

function makeCancelled(message: string, backendCancelled = false): TaskFailure {
  return makeFailure({ message, cancelled: true, backendCancelled, skipped: false });
}

function makeError(message: string, error?: unknown): TaskFailure {
  return makeFailure({ message, error, cancelled: false, backendCancelled: false, skipped: false });
}

function useTaskHandlerInternal(): {
  runTask: <R, M extends TaskMeta>(task: () => Promise<{ taskId: number }>, options: RunTaskOptions<M>) => Promise<TaskResult<R>>;
  cancelTask: (task: Task<TaskMeta>) => Promise<boolean>;
  cancelTaskByTaskType: (taskTypes: TaskType | TaskType[]) => Promise<void>;
  handleResult: (result: TaskActionResult<any>, task: Task<TaskMeta>) => void;
} {
  const handlers: Record<string, (result: ActionResult<any>, meta: any) => void> = {};
  const store = useTaskStore();
  const api = useTaskApi();

  function handlerKey(type: TaskType, taskId?: string): string {
    return taskId ? `${type}-${taskId}` : `${type}`;
  }

  function registerHandler<R, M extends TaskMeta>(
    type: TaskType,
    handlerImpl: (actionResult: TaskActionResult<R>, meta: M) => void,
    taskId?: string,
  ): void {
    const key = handlerKey(type, taskId);
    if (!taskId && key in handlers && checkIfDevelopment()) {
      logger.warn(
        `[TaskHandler] Overwriting existing handler for ${TaskType[type]}. `
        + `This may cause a leaked promise. Consider using unique: false if multiple tasks of this type run concurrently.`,
      );
    }
    handlers[key] = handlerImpl;
  }

  function unregisterHandler(type: TaskType, taskId?: string): void {
    const key = handlerKey(type, taskId);
    delete handlers[key];
  }

  function handleResult(result: TaskActionResult<any>, task: Task<TaskMeta>): void {
    if (task.meta.ignoreResult) {
      store.remove(task.id);
      return;
    }

    const handler = handlers[task.type] ?? handlers[handlerKey(task.type, `${task.id}`)];

    if (handler)
      handler(result, task.meta);
    /* c8 ignore next 3 */
    else
      logger.warn(`missing handler for ${TaskType[task.type]} with id ${task.id}`);

    store.remove(task.id);
  }

  async function runTask<R, M extends TaskMeta>(
    task: () => Promise<{ taskId: number }>,
    options: RunTaskOptions<M>,
  ): Promise<TaskResult<R>> {
    const { type, meta, unique = true, guard = true } = options;

    if (guard && store.isTaskRunning(type, meta))
      return makeSkipped('Task already running');

    const { taskId } = await task();

    store.addTask(taskId, type, meta);

    return new Promise<TaskResult<R>>((resolve) => {
      const resolverTaskId = unique ? undefined : taskId.toString();

      registerHandler<R, M>(
        type,
        (actionResult, _meta) => {
          unregisterHandler(type, resolverTaskId);

          const { message, result, error } = actionResult;

          if (error) {
            resolve(makeError(error.message ?? '', error));
          }
          else if (result === null) {
            if (message === USER_CANCELLED_TASK) {
              if (checkIfDevelopment() && !import.meta.env.VITE_TEST)
                logger.debug(`Request cancelled -> task_id: ${taskId}, task_type: ${TaskType[type]}`);

              resolve(makeCancelled('Request cancelled'));
            }
            else if (message) {
              resolve(makeError(message));
            }
            else {
              resolve(makeCancelled(`Backend cancelled task_id: ${taskId}, task_type: ${TaskType[type]}`, true));
            }
          }
          else {
            resolve({ success: true, result, message: message || undefined });
          }
        },
        resolverTaskId,
      );
    });
  }

  async function cancelTask(task: Task<TaskMeta>): Promise<boolean> {
    const { id, meta, type } = task;

    if (!store.isTaskRunning(type, meta))
      return false;

    try {
      const deleted = await api.cancelAsyncTask(id);

      if (deleted) {
        const handler = handlers[type] ?? handlers[handlerKey(type, `${id}`)];
        if (!handler) {
          store.remove(id);
        }
        else {
          store.lock(id);
          handleResult({ message: USER_CANCELLED_TASK, result: null }, task);
          store.unlock(id);
        }
      }

      return deleted;
    }
    catch (error_: any) {
      if (error_ instanceof TaskNotFoundError)
        store.remove(id);

      return false;
    }
  }

  async function cancelTaskByTaskType(taskTypes: TaskType | TaskType[]): Promise<void> {
    const types = arrayify(taskTypes);
    const taskList = get(store.tasks).filter(item => types.includes(item.type));
    await Promise.allSettled(taskList.map(async task => cancelTask(task)));
  }

  return {
    cancelTask,
    cancelTaskByTaskType,
    handleResult,
    runTask,
  };
}

export const useTaskHandler = createSharedComposable(useTaskHandlerInternal);
