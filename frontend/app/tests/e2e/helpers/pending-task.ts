/**
 * The id of the async task an `async_query` response started, if it started one.
 *
 * @remarks
 * Task ids start at 0, and a fresh backend's first task is the account it creates. Tested for
 * truthiness, that id reads as "no task", so the helper returns before the account is unlocked and
 * every call after it runs against a backend that is still unlocking.
 */
export function pendingTaskId(body: { result?: { task_id?: unknown } | null }): number | undefined {
  const taskId = body.result?.task_id;
  return typeof taskId === 'number' ? taskId : undefined;
}
