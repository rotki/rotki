import { type ActionResult, assert } from '@rotki/common';
import dayjs from 'dayjs';
import { isTimeoutError } from '@/modules/core/api/with-retry';
import { logger } from '@/modules/core/common/logging/logging';
import { TaskType } from '@/modules/core/tasks/task-type';
import { type Task, type TaskMeta, TaskNotFoundError } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import { useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

const UNKNOWN_TASK_THRESHOLD_SECONDS = 30;
const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 8000;

type ErrorHandler = (task: Task<TaskMeta>, message?: string) => ActionResult<unknown>;

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

function useTaskMonitorInternal(): {
  monitor: () => Promise<void>;
} {
  const isRunning = shallowRef<boolean>(false);
  const store = useTaskStore();
  const { handleResult } = useTaskHandler();
  const api = useTaskApi();
  const { error } = useError();

  function computeBackoff(timeoutCount: number): number {
    return Math.min(INITIAL_BACKOFF_MS * 2 ** timeoutCount, MAX_BACKOFF_MS);
  }

  async function processTask(task: Task<TaskMeta>): Promise<void> {
    store.lock(task.id);
    store.removeFromUnknownTasks(task.id);

    try {
      const result = await api.queryTaskResult(task.id);
      assert(result !== null);
      handleResult(result, task);
    }
    catch (error_: any) {
      if (error_ instanceof TaskNotFoundError) {
        store.remove(task.id);
        handleResult(error(task, error_.message), task);
      }
      else if (isTimeoutError(error_)) {
        const count = store.getTimeoutCount(task.id);
        store.setTimeoutCount(task.id, count + 1);
        const backoffMs = computeBackoff(count);
        logger.debug(`[TaskMonitor] Timeout for task ${task.id} (${TaskType[task.type]}), retry in ${backoffMs}ms`);
        await new Promise<void>(resolve => setTimeout(resolve, backoffMs));
      }
      else {
        store.remove(task.id);
        handleResult({ error: error_, message: error_.message, result: null }, task);
      }
    }
    store.unlock(task.id);
  }

  async function handleTasks(ids: number[]): Promise<PromiseSettledResult<void>[]> {
    const taskMap = get(store.taskById);
    return Promise.allSettled(ids.map(async id => processTask(taskMap[id])));
  }

  async function consumeUnknownTasks(ids: number[]): Promise<void> {
    if (ids.length === 0)
      return;

    logger.warn(`the following task ids were not known to the frontend ${ids.join(', ')}`);

    for (const id of ids) {
      await api.queryTaskResult(id);
      store.remove(id);
    }
  }

  /**
   * To avoid certain race conditions where the backend manages to answer before the frontend
   * registers the task, we are keeping a map of unknown tasks along with the time first seen.
   *
   * @param ids The array of the unknown task ids
   * @returns The array of the unknown ids that are past the threshold.
   */
  function checkUnknownTasksPastThreshold(ids: number[]): number[] {
    const tasks = { ...get(store.unknownTasks) };

    const pastThreshold: number[] = [];
    const epoch = dayjs().unix();
    for (const id of ids) {
      if (!tasks[id]) {
        tasks[id] = epoch;
      }
      else if (tasks[id] < epoch - UNKNOWN_TASK_THRESHOLD_SECONDS) {
        delete tasks[id];
        pastThreshold.push(id);
      }
    }

    store.setUnknownTasks(tasks);
    return pastThreshold;
  }

  async function monitor(): Promise<void> {
    if ((!get(store.hasRunningTasks) && !get(store.hasUnknownTasks)) || get(isRunning))
      return;

    set(isRunning, true);
    try {
      const { completed } = await api.queryTasks();
      const { ready, unknown } = store.filterTasks(completed);
      await handleTasks(ready);
      await consumeUnknownTasks(checkUnknownTasksPastThreshold(unknown));
    }
    catch (error_: any) {
      logger.error(error_);
    }

    set(isRunning, false);
  }

  return { monitor };
}

export const useTaskMonitor = createSharedComposable(useTaskMonitorInternal);
