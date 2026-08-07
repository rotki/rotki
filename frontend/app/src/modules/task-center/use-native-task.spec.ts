import type { ResultAsync } from 'plainfp/result-async';
import { err, isErr, isOk, ok, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { assert, describe, expect, it, vi } from 'vitest';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId } from './core/types';
import { useNativeTask } from './use-native-task';
import { useTaskOrchestrator } from './use-task-orchestrator';

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

  describe('reset', () => {
    /** Only the orchestrator can settle this, which is the whole point of the two tests below. */
    const neverSettles = async (): ResultAsync<void, TaskError> => new Promise<Result<void, TaskError>>(() => {});

    // Logout resets the orchestrator while work is still in flight. The caller of that work is
    // awaiting a promise only the orchestrator can settle, and the id is held in `inflight` until
    // it settles — so if reset drops the record without settling the caller, that id is poisoned
    // for the life of the process and every later submit dedups onto a promise that never
    // resolves. In the app that stalls `fetchCached()` on its first await, so the accounts are
    // never fetched and the whole post-login session sits on a spinner.
    it('should settle a caller waiting on work that reset dropped', async () => {
      const { submitTask } = useNativeTask();
      const orchestrator = useTaskOrchestrator();
      const id = makeActivityId(ActivityKind.PRICES, 'reset-settles');

      // Nothing but the orchestrator can settle this.
      const outcome = submitTask({
        id,
        kind: ActivityKind.PRICES,
        run: neverSettles,
        title: 'prices',
      });

      orchestrator.reset();

      const raced = await Promise.race([
        outcome.then(() => 'settled'),
        new Promise<string>((resolve) => {
          setTimeout(resolve, 50, 'HUNG');
        }),
      ]);

      expect(raced).toBe('settled');
    });

    it('should let the same activity run again after reset', async () => {
      const { submitTask } = useNativeTask();
      const orchestrator = useTaskOrchestrator();
      const id = makeActivityId(ActivityKind.PRICES, 'reset-reruns');

      // Awaited only after the reset releases it; the assertion is about the SECOND submit.
      const abandoned = submitTask({
        id,
        kind: ActivityKind.PRICES,
        run: neverSettles,
        title: 'prices',
      });

      orchestrator.reset();
      await abandoned;

      // The id must be free again, or this dedups onto the abandoned promise and never runs.
      const run = vi.fn(async () => ok(undefined));
      await submitTask({ id, kind: ActivityKind.PRICES, run, title: 'prices' });

      expect(run).toHaveBeenCalledOnce();
    });
  });
});
