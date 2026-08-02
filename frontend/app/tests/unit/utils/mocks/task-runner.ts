import { type Mock, vi } from 'vitest';

export interface TaskRunnerOptions {
  /** The spy `runTask` delegates its return value to (create with `vi.fn()`). */
  runTask?: Mock;
  cancelTaskById?: Mock;
  handleResult?: Mock;
  /**
   * When `true` (default) the stubbed `runTask` awaits the passed `taskFn`
   * before resolving, matching production. Set `false` for specs that assert
   * the callback must NOT auto-run.
   */
  invoke?: boolean;
}

/**
 * Builds the `useTaskHandler` mock used by the orchestration specs, replacing
 * the verbatim `runTask: async taskFn => { await taskFn(); return runTaskMock() }`
 * block copied byte-for-byte across the suite.
 *
 * The spy stands in for the real runner, so it resolves a `Result<R, TaskError>`:
 * `ok(value)` for success, `err(TaskFailed({ message }))` / `err(Cancelled({ message }))`
 * for the failure tails.
 *
 * Call it inside a `vi.mock` factory, spreading the original module so unrelated
 * exports survive. Declare the spy with `vi.hoisted` so it exists before the
 * factory reads it (a plain `const` hits a temporal-dead-zone error):
 *
 * ```ts
 * const { runTaskMock } = vi.hoisted(() => ({ runTaskMock: vi.fn() }));
 * vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal =>
 *   mockUseTaskHandler(await importOriginal(), { runTask: runTaskMock }),
 * );
 * ```
 */
export function mockUseTaskHandler(
  original: Record<string, unknown>,
  options: TaskRunnerOptions = {},
): Record<string, unknown> {
  const runTask = options.runTask ?? vi.fn();
  const invoke = options.invoke ?? true;

  return {
    ...original,
    useTaskHandler: vi.fn().mockReturnValue({
      cancelTaskById: options.cancelTaskById ?? vi.fn(),
      handleResult: options.handleResult ?? vi.fn(),
      runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<any> => {
        if (invoke)
          await taskFn();

        return runTask(taskFn, ...rest);
      },
    }),
  };
}
