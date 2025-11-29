import { type ActionResult, assert } from '@rotki/common';
import { checkIfDevelopment } from '@shared/utils';
import dayjs from 'dayjs';
import { find, toArray } from 'es-toolkit/compat';
import { useTaskApi } from '@/composables/api/task';
import { isTimeoutError } from '@/modules/api/with-retry';
import {
  BackendCancelledTaskError,
  type Task,
  type TaskMap,
  type TaskMeta,
  TaskNotFoundError,
  UserCancelledTaskError,
} from '@/types/task';
import { TaskType } from '@/types/task-type';
import { arrayify } from '@/utils/array';
import { removeKey } from '@/utils/data';
import { logger } from '@/utils/logging';

const USER_CANCELLED_TASK = 'task_cancelled_by_user';
const TIMEOUT_THRESHOLD = 3;

type ErrorHandler = (task: Task<TaskMeta>, message?: string) => ActionResult<unknown>;

interface TaskResponse<R, M extends TaskMeta> {
  result: R;
  meta: M;
  message?: string;
}

interface TaskActionResult<T> extends ActionResult<T> {
  error?: any;
}

function unlockTask(lockedTasks: Ref<number[]>, taskId: number): number[] {
  const locked = [...get(lockedTasks)];
  const idIndex = locked.indexOf(taskId);
  locked.splice(idIndex, 1);
  return locked;
}

function useError(): { error: ErrorHandler } {
  const { t } = useI18n({ useScope: 'global' });
  const error: ErrorHandler = (task, error) => ({
    message: t('task_manager.error', {
      error,
      taskId: task.id,
      title: task.meta.title,
    }),
    result: {},
  });
  return { error };
}

export const useTaskStore = defineStore('tasks', () => {
  const locked = ref<number[]>([]);
  const tasks = ref<TaskMap<TaskMeta>>({});
  const unknownTasks = ref<Record<number, number>>({});
  const timeouts = ref<Record<number, number>>({});
  const handlers: Record<string, (result: ActionResult<any>, meta: any) => void> = {};
  let isRunning = false;

  const { error } = useError();
  const api = useTaskApi();

  const registerHandler = <R, M extends TaskMeta>(
    task: TaskType,
    handlerImpl: (actionResult: TaskActionResult<R>, meta: M) => void,
    taskId?: string,
  ): void => {
    const identifier = taskId ? `${task}-${taskId}` : task;
    handlers[identifier] = handlerImpl;
  };

  const unregisterHandler = (task: TaskType, taskId?: string): void => {
    const identifier = taskId ? `${task}-${taskId}` : task;
    delete handlers[identifier];
  };

  const add = (task: Task<TaskMeta>): void => {
    const update: TaskMap<TaskMeta> = {};
    update[task.id] = task;
    set(tasks, { ...get(tasks), ...update });
  };

  const lock = (taskId: number): void => {
    set(locked, [...get(locked), taskId]);
  };

  const unlock = (taskId: number): void => {
    set(locked, unlockTask(locked, taskId));
  };

  const remove = (taskId: number): void => {
    set(tasks, removeKey(get(tasks), taskId));
    set(timeouts, removeKey(get(timeouts), taskId));
    unlock(taskId);
  };

  const checkIfTaskIsRunning = (
    runningTasks: TaskMap<TaskMeta>,
    type: TaskType,
    meta: Record<string, any> = {},
  ): boolean => !!find(runningTasks, (item) => {
    const sameType = item.type === type;
    const keys = Object.keys(meta);
    if (keys.length === 0)
      return sameType;

    return (
      sameType
      && keys.every(
        key =>
        // @ts-expect-error meta key has any type
          key in item.meta && item.meta[key] === meta[key],
      )
    );
  });

  const isTaskRunning = (
    type: TaskType,
    meta: Record<string, any> = {},
  ): boolean => checkIfTaskIsRunning(get(tasks), type, meta);

  const useIsTaskRunning = (
    type: TaskType,
    meta: MaybeRef<Record<string, any>> = {},
  ): ComputedRef<boolean> => computed<boolean>(() => checkIfTaskIsRunning(get(tasks), type, get(meta)));

  const metadata = <T extends TaskMeta>(type: TaskType): T | undefined => {
    const task = find(Object.values(get(tasks)), item => item.type === type);
    if (task)
      return task.meta as T;

    return undefined;
  };

  const hasRunningTasks = computed<boolean>(() => Object.keys(get(tasks)).length > 0);
  const hasUnknownTasks = computed<boolean>(() => Object.keys(get(unknownTasks)).length > 0);

  const taskList = computed(() => toArray(get(tasks)));

  const addTask = <M extends TaskMeta>(id: number, type: TaskType, meta: M): void => {
    assert(!(id === null || id === undefined), `missing id for ${TaskType[type]} with ${JSON.stringify(meta)}`);

    add({
      id,
      meta,
      time: dayjs().valueOf(),
      type,
    });
  };

  const handleResult = (result: TaskActionResult<any>, task: Task<TaskMeta>): void => {
    if (task.meta.ignoreResult) {
      remove(task.id);
      return;
    }

    const handler = handlers[task.type] ?? handlers[`${task.type}-${task.id}`];

    if (handler)
      handler(result, task.meta);
    /* c8 ignore next 5 */ else logger.warn(`missing handler for ${TaskType[task.type]} with id ${task.id}`);

    remove(task.id);
  };

  const cancelTask = async (task: Task<TaskMeta>): Promise<boolean> => {
    const { id, meta, type } = task;

    if (!isTaskRunning(type, meta))
      return false;

    try {
      const deleted = await api.cancelAsyncTask(id);

      if (deleted) {
        const handler = handlers[type] ?? handlers[`${type}-${id}`];
        if (!handler) {
          remove(task.id);
        }
        else {
          lock(id);
          handleResult({ message: USER_CANCELLED_TASK, result: null }, task);
          unlock(id);
        }
      }

      return deleted;
    }
    catch (error_: any) {
      if (error_ instanceof TaskNotFoundError)
        remove(task.id);

      return false;
    }
  };

  const cancelTaskByTaskType = async (taskTypes: TaskType | TaskType[]): Promise<void> => {
    const types = arrayify(taskTypes);

    const tasks = get(taskList).filter(item => types.includes(item.type));

    await Promise.allSettled(tasks.map(async task => cancelTask(task)));
  };

  const awaitTask = async <R, M extends TaskMeta>(
    id: number,
    type: TaskType,
    meta: M,
    nonUnique = false,
  ): Promise<TaskResponse<R, M>> => {
    addTask(id, type, meta);

    return new Promise<TaskResponse<R, M>>((resolve, reject) => {
      registerHandler<R, M>(
        type,
        (actionResult, meta) => {
          unregisterHandler(type, id.toString());
          const { message, result } = actionResult;

          if (actionResult.error) {
            reject(actionResult.error);
          }
          else if (result === null) {
            let errorMessage: string;
            if (message) {
              if (message === USER_CANCELLED_TASK) {
                const msg = 'Request cancelled';
                if (checkIfDevelopment() && !import.meta.env.VITE_TEST)
                  logger.debug(`${msg} -> task_id: ${id}, task_type: ${TaskType[type]}`);

                reject(new UserCancelledTaskError(msg));
                return;
              }
              errorMessage = message;
              reject(new Error(errorMessage));
            }
            else {
              reject(new BackendCancelledTaskError(`Backend cancelled task_id: ${id}, task_type: ${TaskType[type]}`));
            }
          }
          else {
            resolve({ message, meta, result });
          }
        },
        nonUnique ? id.toString() : undefined,
      );
    });
  };

  const filterTasks = (taskIds: number[]): { ready: number[]; unknown: number[] } => {
    const lockedTasks = get(locked);
    const pendingTasks = get(tasks);
    return {
      ready: taskIds.filter(id => !lockedTasks.includes(id) && pendingTasks[id] && pendingTasks[id].id !== null),
      unknown: taskIds.filter(id => !lockedTasks.includes(id) && !pendingTasks[id]),
    };
  };

  function removeFromUnknownTasks(taskId: number): void {
    const unknown = { ...get(unknownTasks) };
    if (!unknown[taskId])
      return;

    delete unknown[taskId];
    set(unknownTasks, unknown);
  }

  const processTask = async (task: Task<TaskMeta>): Promise<void> => {
    lock(task.id);
    removeFromUnknownTasks(task.id);

    try {
      const result = await api.queryTaskResult(task.id);
      assert(result !== null);
      handleResult(result, task);
    }
    catch (error_: any) {
      if (error_ instanceof TaskNotFoundError) {
        remove(task.id);
        handleResult(error(task, error_.message), task);
      }
      else {
        if (isTimeoutError(error_)) {
          const totalTimeouts = (get(timeouts)[task.id] ?? 0) + 1;
          if (totalTimeouts >= TIMEOUT_THRESHOLD) {
            remove(task.id);
            handleResult({ error: error_, message: error_.message, result: null }, task);
          }
          else {
            set(timeouts, { ...get(timeouts), [task.id]: totalTimeouts });
          }
        }
        else {
          remove(task.id);
          handleResult({ error: error_, message: error_.message, result: null }, task);
        }
      }
    }
    unlock(task.id);
  };

  const handleTasks = async (ids: number[]): Promise<PromiseSettledResult<void>[]> => {
    const taskMap = get(tasks);
    return Promise.allSettled(ids.map(async id => processTask(taskMap[id])));
  };

  const consumeUnknownTasks = async (ids: number[]): Promise<void> => {
    if (ids.length === 0)
      return;

    logger.warn(`the following task ids were not known to the frontend ${ids.join(', ')}`);

    for (const id of ids) {
      await api.queryTaskResult(id);
      remove(id);
    }
  };

  /**
   * To avoid certain race conditions where the backend manages to answer before the frontend
   * registers the task, we are keeping a map of unknown tasks along with the time first seen.
   *
   * @param ids The array of the unknown task ids
   * @returns The array of the unknown ids that are past the threshold.
   */
  const checkUnknownTasksPastThreshold = (ids: number[]): number[] => {
    const tasks = { ...get(unknownTasks) };

    const pastThreshold: number[] = [];
    const epoch = dayjs().unix();
    ids.forEach((id) => {
      if (!tasks[id]) {
        tasks[id] = epoch;
      }
      else {
        if (tasks[id] < epoch - 30) {
          delete tasks[id];
          pastThreshold.push(id);
        }
      }
    });

    set(unknownTasks, tasks);
    return pastThreshold;
  };

  const monitor = async (): Promise<void> => {
    if ((!get(hasRunningTasks) && !get(hasUnknownTasks)) || isRunning)
      return;

    isRunning = true;
    try {
      const { completed } = await api.queryTasks();
      const { ready, unknown } = filterTasks(completed);
      await handleTasks(ready);
      await consumeUnknownTasks(checkUnknownTasksPastThreshold(unknown));
    }
    catch (error_: any) {
      logger.error(error_);
    }

    isRunning = false;
  };

  return {
    add,
    addTask,
    awaitTask,
    cancelTask,
    cancelTaskByTaskType,
    hasRunningTasks,
    isTaskRunning,
    locked,
    metadata,
    monitor,
    remove,
    taskById: tasks,
    tasks: taskList,
    useIsTaskRunning,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useTaskStore, import.meta.hot));
