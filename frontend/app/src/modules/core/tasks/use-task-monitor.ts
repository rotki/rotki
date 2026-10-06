import { type ActionResult, assert } from '@rotki/common';
import dayjs from 'dayjs';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { isTimeoutError } from '@/modules/core/api/with-retry';
import { logger } from '@/modules/core/common/logging/logging';
import { onSessionEnd } from '@/modules/core/session/session-lifecycle';
import { type Task, TaskNotFoundError } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import { useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

const UNKNOWN_TASK_THRESHOLD_SECONDS = 30;
const INITIAL_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 8000;

type ErrorHandler = (task: Task, message?: string) => ActionResult<unknown>;

/**
 * The payload for a task the backend has forgotten.
 *
 * `result` must stay `null`. `use-task-handler` branches on `result !== null` *before* it looks
 * at `message`, so an empty object here resolved the producer's promise as `ok({})` — a task the
 * backend has forgotten was reported as a success carrying nothing, and the message below (the
 * only thing saying anything went wrong) was discarded. `null` reaches the `message` branch, which
 * yields `TaskFailed` and settles the activity FAILED.
 */
function useError(): { error: ErrorHandler } {
  const { t } = useI18n({ useScope: 'global' });
  const error: ErrorHandler = (task, error) => ({
    message: t('task_manager.error', {
      error,
      taskId: task.id,
      title: task.label,
    }),
    result: null,
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
  const retryTimers = new Map<number, ReturnType<typeof setTimeout>>();

  onSessionEnd('task-monitor', cancelRetries);
  tryOnScopeDispose(cancelRetries);

  function computeBackoff(timeoutCount: number): number {
    return Math.min(INITIAL_BACKOFF_MS * 2 ** timeoutCount, MAX_BACKOFF_MS);
  }

  /**
   * Keeps a task whose result fetch timed out locked for `backoffMs`, so later passes skip it.
   *
   * @remarks
   * The pass that hit the timeout returns at once rather than waiting out the backoff, so the
   * monitor never sits idle on one task while the others finish, and a logout cannot leave a pass
   * running into the next session.
   */
  function holdForRetry(taskId: number, backoffMs: number): void {
    clearTimeout(retryTimers.get(taskId));
    retryTimers.set(taskId, setTimeout(() => {
      retryTimers.delete(taskId);
      store.unlock(taskId);
    }, backoffMs));
  }

  function cancelRetries(): void {
    for (const timer of retryTimers.values())
      clearTimeout(timer);
    retryTimers.clear();
  }

  async function processTask(task: Task): Promise<void> {
    store.lock(task.id);
    store.removeFromUnknownTasks(task.id);

    try {
      const result = await api.queryTaskResult(task.id);
      assert(result !== null);
      handleResult(result, task.id);
    }
    catch (error_: any) {
      if (error_ instanceof TaskNotFoundError) {
        store.remove(task.id);
        handleResult(error(task, error_.message), task.id);
      }
      else if (isTimeoutError(error_)) {
        const count = store.getTimeoutCount(task.id);
        store.setTimeoutCount(task.id, count + 1);
        const backoffMs = computeBackoff(count);
        logger.debug(`[TaskMonitor] Timeout for task ${task.id} (${task.label}), retry in ${backoffMs}ms`);
        holdForRetry(task.id, backoffMs);
        return;
      }
      else if (!isRequestCancellation(error_)) {
        store.remove(task.id);
        handleResult({ error: error_, message: error_.message, result: null }, task.id);
      }
    }
    store.unlock(task.id);
  }

  /**
   * Settles every task the backend no longer lists as cancelled by the backend.
   *
   * @remarks
   * The backend lists a task, as pending or completed, from its creation until its outcome is
   * fetched. A task missing from both was dropped without an outcome, as a backend restart that
   * keeps the session does, and nothing would ever settle it. Only tasks known
   * before the listing was requested are judged by it: one added since may be newer than the list.
   * A locked task is having its outcome fetched or waiting to retry.
   *
   * @param known - the task ids the store held when the listing was requested
   * @param listed - the ids the listing returned, pending and completed
   */
  function settleDropped(known: number[], listed: Set<number>): void {
    const lockedSet = get(store.locked);
    const taskMap = get(store.taskById);
    for (const id of known) {
      if (listed.has(id) || lockedSet.has(id) || !taskMap[id])
        continue;

      logger.warn(`[TaskMonitor] The backend no longer lists task ${id} (${taskMap[id].label})`);
      handleResult({ message: '', result: null }, id);
    }
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
   * @param ids - the unknown task ids seen in this poll
   * @returns those that have been unknown for longer than the threshold
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
      const known = get(store.tasks).map(task => task.id);
      const { completed, pending } = await api.queryTasks();
      settleDropped(known, new Set([...pending, ...completed]));
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
