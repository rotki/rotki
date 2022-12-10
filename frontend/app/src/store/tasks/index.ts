import { type ActionResult } from '@rotki/common/lib/data';
import dayjs from 'dayjs';
import find from 'lodash/find';
import toArray from 'lodash/toArray';
import { type ComputedRef, type Ref } from 'vue';

import { api } from '@/services/rotkehlchen-api';
import { TaskNotFoundError } from '@/services/types-api';
import { SyncConflictError } from '@/types/login';
import { type Task, type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import { checkIfDevelopment } from '@/utils/env-utils';
import { logger } from '@/utils/logging';

export type TaskMap<T extends TaskMeta> = Record<number, Task<T>>;

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
  const { tc } = useI18n();
  const error: ErrorHandler = (task, error) => ({
    result: {},
    message: tc('task_manager.error', 0, {
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
export const useTasks = defineStore('tasks', () => {
  const locked = ref<number[]>([]);
  const tasks = ref<TaskMap<TaskMeta>>({});
  const handlers: Record<string, (result: any, meta: any) => void> = {};
  let isRunning = false;

  const { error } = useError();

  const registerHandler = <R, M extends TaskMeta>(
    task: TaskType,
    handlerImpl: (actionResult: ActionResult<R>, meta: M) => void,
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
    computed(() => {
      return !!find(get(tasks), item => {
        const sameType = item.type === type;
        const keys = Object.keys(meta);
        if (keys.length === 0) return sameType;

        return (
          sameType &&
          keys.every(key => {
            // @ts-ignore
            return key in item.meta && item.meta[key] === meta[key];
          })
        );
      });
    });

  const metadata = <T extends TaskMeta>(type: TaskType): T | undefined => {
    const task = find(get(tasks), item => item.type === type);
    if (task) {
      return task.meta as T;
    }
    return undefined;
  };

  const hasRunningTasks = computed(() => {
    return Object.keys(get(tasks)).length > 0;
  });

  const taskList = computed(() => toArray(get(tasks)));

  function addTask<M extends TaskMeta>(
    id: number,
    type: TaskType,
    meta: M
  ): void {
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
  }

  async function awaitTask<R, M extends TaskMeta>(
    id: number,
    type: TaskType,
    meta: M,
    nonUnique = false
  ): Promise<TaskResponse<R, M>> {
    addTask(id, type, meta);

    return new Promise<TaskResponse<R, M>>((resolve, reject) => {
      registerHandler<R, M>(
        type,
        (actionResult, meta) => {
          unregisterHandler(type, id.toString());
          const { result, message } = actionResult;
          if (result === null) {
            let errorMessage: string;
            if (message) {
              errorMessage = message;
            } else {
              errorMessage = `No message returned for ${TaskType[type]} with id ${id}`;
            }

            if (checkIfDevelopment()) {
              errorMessage += `: ${JSON.stringify(meta)}`;
            }

            reject(new Error(errorMessage));
          } else {
            resolve({ result, meta, message });
          }
        },
        nonUnique ? id.toString() : undefined
      );
    });
  }

  function filterOutUnprocessable(taskIds: number[]): number[] {
    const lockedTasks = get(locked);
    const pendingTasks = get(tasks);
    return taskIds.filter(
      id =>
        !lockedTasks.includes(id) &&
        pendingTasks[id] &&
        pendingTasks[id].id !== null
    );
  }

  async function handleTasks(
    ids: number[]
  ): Promise<PromiseSettledResult<void>[]> {
    return Promise.allSettled(ids.map(id => processTask(get(tasks)[id])));
  }

  function handleResult(result: ActionResult<any>, task: Task<TaskMeta>): void {
    if (task.meta.ignoreResult) {
      remove(task.id);
      return;
    }

    const handler = handlers[task.type] ?? handlers[`${task.type}-${task.id}`];

    if (!handler) {
      logger.warn(
        `missing handler for ${TaskType[task.type]} with id ${task.id}`
      );
      remove(task.id);
      return;
    }

    try {
      handler(result, task.meta);
    } catch (e: any) {
      handler(error(task, e.message), task.meta);
      logger.error(
        `Error while running task ${TaskType[task.type]} with id ${task.id}`,
        e
      );
    }
    remove(task.id);
  }

  async function processTask(task: Task<TaskMeta>): Promise<void> {
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
      } else if (e instanceof SyncConflictError) {
        handleResult({ message: e.message, result: e.payload }, task);
      }
    }
    unlock(task.id);
  }

  const monitor = async (): Promise<void> => {
    if (!get(hasRunningTasks) || isRunning) {
      return;
    }

    isRunning = true;
    try {
      const { completed } = await api.queryTasks();
      await handleTasks(filterOutUnprocessable(completed));
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
    lock,
    unlock,
    isTaskRunning,
    hasRunningTasks,
    metadata,
    addTask,
    awaitTask,
    monitor
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useTasks, import.meta.hot));
}
