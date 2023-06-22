import { type ActionResult } from '@rotki/common/lib/data';
import dayjs from 'dayjs';
import find from 'lodash/find';
import toArray from 'lodash/toArray';
import {
  BackendCancelledTaskError,
  type Task,
  type TaskMap,
  type TaskMeta,
  TaskNotFoundError
} from '@/types/task';
import { TaskType } from '@/types/task-type';

const unlockTask = (lockedTasks: Ref<number[]>, taskId: number): number[] => {
  const locked = [...get(lockedTasks)];
  const idIndex = locked.indexOf(taskId);
  locked.splice(idIndex, 1);
  return locked;
};

type ErrorHandler = (
  task: Task<TaskMeta>,
  message?: string
) => ActionResult<{}>;

const useError = (): { error: ErrorHandler } => {
  const { t } = useI18n();
  const error: ErrorHandler = (task, error) => ({
    result: {},
    message: t('task_manager.error', {
      taskId: task.id,
      title: task.meta.title,
      error
    })
  });
  return {
    error
  };
};

interface TaskResponse<R, M extends TaskMeta> {
  result: R;
  meta: M;
  message?: string;
}

interface TaskActionResult<T> extends ActionResult<T> {
  error?: any;
}

export const useTaskStore = defineStore('tasks', () => {
  const locked = ref<number[]>([]);
  const tasks = ref<TaskMap<TaskMeta>>({});
  const handlers: Record<
    string,
    (result: ActionResult<any>, meta: any) => void
  > = {};
  let isRunning = false;

  const { error } = useError();

  const api = useTaskApi();

  const registerHandler = <R, M extends TaskMeta>(
    task: TaskType,
    handlerImpl: (actionResult: TaskActionResult<R>, meta: M) => void,
    taskId?: string
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
    const remainingTasks = { ...get(tasks) };
    delete remainingTasks[taskId];
    set(tasks, remainingTasks);
    set(locked, unlockTask(locked, taskId));
  };

  const isTaskRunning = (
    type: TaskType,
    meta: Record<string, any> = {}
  ): ComputedRef<boolean> =>
    computed(
      () =>
        !!find(get(tasks), item => {
          const sameType = item.type === type;
          const keys = Object.keys(meta);
          if (keys.length === 0) {
            return sameType;
          }

          return (
            sameType &&
            keys.every(
              key =>
                // @ts-ignore
                key in item.meta && item.meta[key] === meta[key]
            )
          );
        })
    );

  const metadata = <T extends TaskMeta>(type: TaskType): T | undefined => {
    const task = find(get(tasks), item => item.type === type);
    if (task) {
      return task.meta as T;
    }
    return undefined;
  };

  const hasRunningTasks = computed(() => Object.keys(get(tasks)).length > 0);

  const taskList = computed(() => toArray(get(tasks)));

  const addTask = <M extends TaskMeta>(
    id: number,
    type: TaskType,
    meta: M
  ): void => {
    assert(
      !(id === null || id === undefined),
      `missing id for ${TaskType[type]} with ${JSON.stringify(meta)}`
    );

    add({
      id,
      type,
      meta,
      time: dayjs().valueOf()
    });
  };

  const awaitTask = async <R, M extends TaskMeta>(
    id: number,
    type: TaskType,
    meta: M,
    nonUnique = false
  ): Promise<TaskResponse<R, M>> => {
    addTask(id, type, meta);

    return new Promise<TaskResponse<R, M>>((resolve, reject) => {
      registerHandler<R, M>(
        type,
        (actionResult, meta) => {
          unregisterHandler(type, id.toString());
          const { result, message } = actionResult;

          if (actionResult.error) {
            reject(actionResult.error);
          } else if (result === null) {
            let errorMessage: string;
            if (message) {
              errorMessage = message;
              /* c8 ignore next 5 */
              if (checkIfDevelopment() && !import.meta.env.VITE_TEST) {
                errorMessage += `::dev_only_msg_part:: task_id: ${id}, task_type: ${
                  TaskType[type]
                }, meta: ${JSON.stringify(meta)}`;
              }
              reject(new Error(errorMessage));
            } else {
              reject(
                new BackendCancelledTaskError(
                  `Backend cancelled task_id: ${id}, task_type: ${TaskType[type]}`
                )
              );
            }
          } else {
            resolve({ result, meta, message });
          }
        },
        nonUnique ? id.toString() : undefined
      );
    });
  };

  const filterTasks = (
    taskIds: number[]
  ): {
    ready: number[];
    unknown: number[];
  } => {
    const lockedTasks = get(locked);
    const pendingTasks = get(tasks);
    return {
      ready: taskIds.filter(
        id =>
          !lockedTasks.includes(id) &&
          pendingTasks[id] &&
          pendingTasks[id].id !== null
      ),
      unknown: taskIds.filter(
        id => !lockedTasks.includes(id) && !pendingTasks[id]
      )
    };
  };

  const handleResult = (
    result: TaskActionResult<any>,
    task: Task<TaskMeta>
  ): void => {
    if (task.meta.ignoreResult) {
      remove(task.id);
      return;
    }

    const handler = handlers[task.type] ?? handlers[`${task.type}-${task.id}`];

    if (handler) {
      handler(result, task.meta);
      /* c8 ignore next 5 */
    } else {
      logger.warn(
        `missing handler for ${TaskType[task.type]} with id ${task.id}`
      );
    }

    remove(task.id);
  };

  const processTask = async (task: Task<TaskMeta>): Promise<void> => {
    lock(task.id);

    try {
      const result = await api.queryTaskResult(task.id);
      assert(result !== null);
      handleResult(result, task);
    } catch (e: any) {
      logger.error('Task handling failed', e);
      if (e instanceof TaskNotFoundError) {
        remove(task.id);
        handleResult(error(task, e.message), task);
      } else {
        handleResult({ message: e.message, result: null, error: e }, task);
      }
    }
    unlock(task.id);
  };

  const handleTasks = async (
    ids: number[]
  ): Promise<PromiseSettledResult<void>[]> => {
    const taskMap = get(tasks);
    return Promise.allSettled(ids.map(id => processTask(taskMap[id])));
  };

  const consumeUnknownTasks = async (ids: number[]): Promise<void> => {
    if (ids.length === 0) {
      return;
    }
    logger.warn(
      `the following task ids where not known to the frontend ${ids.join(', ')}`
    );

    for (const id of ids) {
      await api.queryTaskResult(id);
    }
  };

  const monitor = async (): Promise<void> => {
    if (!get(hasRunningTasks) || isRunning) {
      return;
    }

    isRunning = true;
    try {
      const { completed } = await api.queryTasks();
      const { ready, unknown } = filterTasks(completed);
      await handleTasks(ready);
      await consumeUnknownTasks(unknown);
    } catch (e: any) {
      logger.error(e);
    }

    isRunning = false;
  };

  return {
    tasks: taskList,
    taskById: tasks,
    locked,
    add,
    remove,
    isTaskRunning,
    hasRunningTasks,
    metadata,
    addTask,
    awaitTask,
    monitor
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useTaskStore, import.meta.hot));
}
