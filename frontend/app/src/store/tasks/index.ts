import { ActionResult } from '@rotki/common/lib/data';
import { computed, ref, Ref } from '@vue/composition-api';
import dayjs from 'dayjs';
import find from 'lodash/find';
import toArray from 'lodash/toArray';
import { acceptHMRUpdate, defineStore } from 'pinia';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { TaskNotFoundError } from '@/services/types-api';
import { Task, TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { assert } from '@/utils/assertions';
import { logger } from '@/utils/logging';

export interface TaskMap<T extends TaskMeta> {
  [taskId: number]: Task<T>;
}

const unlockTask = (lockedTasks: Ref<number[]>, taskId: number) => {
  const locked = [...lockedTasks.value];
  const idIndex = locked.findIndex(value => value === taskId);
  locked.splice(idIndex, 1);
  return locked;
};

const error: (task: Task<TaskMeta>, message?: string) => ActionResult<{}> = (
  task,
  error
) => ({
  result: {},
  message: i18n
    .t('task_manager.error', {
      taskId: task.id,
      title: task.meta.title,
      error
    })
    .toString()
});

export const useTasks = defineStore('tasks', () => {
  const locked = ref<number[]>([]);
  const tasks = ref<TaskMap<TaskMeta>>({});
  const handlers: Record<string, (result: any, meta: any) => void> = {};
  let isRunning = false;

  const registerHandler = <R, M extends TaskMeta>(
    task: TaskType,
    handlerImpl: (actionResult: ActionResult<R>, meta: M) => void,
    taskId?: string
  ) => {
    const identifier = taskId ? `${task}-${taskId}` : task;
    handlers[identifier] = handlerImpl;
  };

  const unregisterHandler = (task: TaskType, taskId?: string) => {
    const identifier = taskId ? `${task}-${taskId}` : task;
    delete handlers[identifier];
  };

  const add = (task: Task<TaskMeta>) => {
    const update: TaskMap<TaskMeta> = {};
    update[task.id] = task;
    tasks.value = { ...tasks.value, ...update };
  };
  const lock = (taskId: number) => {
    locked.value = [...locked.value, taskId];
  };
  const unlock = (taskId: number) => {
    locked.value = unlockTask(locked, taskId);
  };
  const remove = (taskId: number) => {
    const remainingTasks = { ...tasks.value };
    delete remainingTasks[taskId];
    tasks.value = remainingTasks;
    locked.value = unlockTask(locked, taskId);
  };

  const isTaskRunning = (type: TaskType) =>
    computed(() => {
      return !!find(tasks.value, item => item.type === type);
    });

  const metadata = <T extends TaskMeta>(type: TaskType) => {
    const task = find(tasks.value, item => item.type === type);
    if (task) {
      return task.meta as T;
    }
    return undefined;
  };

  const hasRunningTasks = computed(() => {
    return Object.keys(tasks.value).length > 0;
  });

  const taskList = computed(() => toArray(tasks.value));

  function addTask<M extends TaskMeta>(id: number, type: TaskType, meta: M) {
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
    nonUnique: boolean = false
  ) {
    addTask(id, type, meta);

    return new Promise<{ result: R; meta: M }>((resolve, reject) => {
      registerHandler<R, M>(
        type,
        (actionResult, meta) => {
          unregisterHandler(type, id.toString());
          const { result, message } = actionResult;
          if (message && result === null) {
            reject(new Error(message));
          } else {
            resolve({ result, meta });
          }
        },
        nonUnique ? id.toString() : undefined
      );
    });
  }

  function filterOutUnprocessable(taskIds: number[]): number[] {
    const lockedTasks = locked.value;
    const pendingTasks = tasks.value;
    return taskIds.filter(
      id =>
        !lockedTasks.includes(id) &&
        pendingTasks[id] &&
        pendingTasks[id].id !== null
    );
  }

  async function handleTasks(ids: number[]) {
    return Promise.allSettled(ids.map(id => processTask(tasks.value[id])));
  }

  function handleResult(result: ActionResult<any>, task: Task<TaskMeta>) {
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

  async function processTask(task: Task<TaskMeta>) {
    lock(task.id);

    try {
      const result = await api.queryTaskResult(task.id, task.meta.numericKeys);
      assert(result !== null);
      handleResult(result, task);
    } catch (e: any) {
      logger.error('Task handling failed', e);
      if (e instanceof TaskNotFoundError) {
        remove(task.id);
        handleResult(error(task, e.message), task);
      }
    }
    unlock(task.id);
  }

  const monitor = async () => {
    if (!hasRunningTasks.value || isRunning) {
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

  const reset = () => {
    tasks.value = {};
    locked.value = [];
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
    monitor,
    reset
  };
});

if (module.hot) {
  module.hot.accept(acceptHMRUpdate(useTasks, module.hot));
}
