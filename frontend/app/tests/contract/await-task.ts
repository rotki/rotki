import type { PendingTask } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';

const POLL_INTERVAL_MS = 250;
const DEFAULT_TIMEOUT_MS = 60_000;

/**
 * Awaits an async-query task the way the app's task store does: poll the
 * tasks endpoint until the id shows up as completed, then unwrap the outcome
 * through queryTaskResult — so the tasks-list shape, the camelCase transform
 * and the outcome envelope are all part of the contract under test. The
 * caller applies the same zod parse the app's call site applies to the
 * returned result.
 */
export async function awaitTaskOutcome<T>(task: PendingTask, timeoutMs: number = DEFAULT_TIMEOUT_MS): Promise<T> {
  const { queryTaskResult, queryTasks } = useTaskApi();
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const status = await queryTasks();
    if (status.completed.includes(task.taskId)) {
      const outcome = await queryTaskResult<T>(task.taskId);
      if (outcome.result === null || outcome.result === undefined)
        throw new Error(`task ${task.taskId} failed: ${outcome.message}`);
      return outcome.result;
    }
    await new Promise(resolve => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  throw new Error(`task ${task.taskId} did not complete within ${timeoutMs}ms`);
}
