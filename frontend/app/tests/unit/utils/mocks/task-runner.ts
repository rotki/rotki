import { type Mock, vi } from 'vitest';

export interface TaskRunnerOptions {
  /** The spy `runTask` delegates its return value to (create with `vi.fn()`). */
  runTask?: Mock;
  cancelTask?: Mock;
  cancelTaskByTaskType?: Mock;
  handleResult?: Mock;
  /**
   * When `true` (default) the stubbed `runTask` awaits the passed `taskFn`
   * before resolving, matching production. Set `false` for specs that assert
   * the callback must NOT auto-run.
   */
  invoke?: boolean;
}

/**
 * Builds the `useTaskHandler` mock used by ~35 orchestration specs, replacing
 * the verbatim `runTask: async taskFn => { await taskFn(); return runTaskMock() }`
 * block copied byte-for-byte across the suite.
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
      runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
        if (invoke)
          await taskFn();

        return runTask(taskFn, ...rest);
      },
      cancelTask: options.cancelTask ?? vi.fn(),
      cancelTaskByTaskType: options.cancelTaskByTaskType ?? vi.fn(),
      handleResult: options.handleResult ?? vi.fn(),
    }),
  };
}
