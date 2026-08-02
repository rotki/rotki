import { err, isErr, isOk, ok } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { assert, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId } from './core/types';
import { useNativeTask } from './use-native-task';

// The handler backs the runner the facade binds to each activity, and the backend abort behind
// `cancel`; the orchestrator stays real.
vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  useTaskHandler: (): Record<string, unknown> => ({
    cancelTaskById: vi.fn(async () => true),
    runTaskResult: vi.fn(),
  }),
}));

describe('useNativeTask', () => {
  it('should run the spec and resolve ok on success', async () => {
    const { submitTask } = useNativeTask();
    const run = vi.fn(async () => ok(undefined));

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.PRICES, 'success'),
      kind: ActivityKind.PRICES,
      run,
      title: 'prices',
    });

    expect(run).toHaveBeenCalledOnce();
    expect(isOk(outcome)).toBe(true);
  });

  it('should resolve with the failure outcome when the spec fails', async () => {
    const { submitTask } = useNativeTask();

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.PRICES, 'failure'),
      kind: ActivityKind.PRICES,
      run: async () => err(TaskFailed({ message: 'boom' })),
      title: 'prices',
    });

    assert(isErr(outcome));
    expect(hasTag(outcome.error, 'TaskFailed')).toBe(true);
  });

  it('should share the in-flight promise for concurrent same-id submits', async () => {
    const { submitTask } = useNativeTask();
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const run = vi.fn(async () => {
      await gate;
      return ok(undefined);
    });
    const spec = {
      id: makeActivityId(ActivityKind.PRICES, 'dup'),
      kind: ActivityKind.PRICES,
      run,
      title: 'prices',
    };

    const first = submitTask(spec);
    const second = submitTask(spec);
    expect(first).toBe(second);

    release();
    await Promise.all([first, second]);
    expect(run).toHaveBeenCalledOnce();
  });
});
