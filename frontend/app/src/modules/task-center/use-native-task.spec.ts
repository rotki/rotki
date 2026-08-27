import type { ResultAsync } from 'plainfp/result-async';
import { neverSettles } from '@test/utils/never-settles';
import { err, isErr, isOk, ok, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { assert, describe, expect, it, vi } from 'vitest';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { ActivityKind, makeActivityId } from './core/types';
import { useNativeTask } from './use-native-task';
import { useTaskOrchestrator } from './use-task-orchestrator';

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

  describe('ctx.cancelled', () => {
    /**
     * Cancelling settles the *record*; it cannot interrupt a running async body, because
     * nothing in JavaScript can. A body with more than one stage therefore runs to completion after
     * the row already says CANCELLED — observed against a real backend as a cancelled chain going
     * on to issue its balance query, `POST /balances/blockchains/eth` landing after the `DELETE`s
     * that aborted its detections.
     */
    it('should tell a running body that it was cancelled', async () => {
      const { cancelActivity, submitTask } = useNativeTask();
      const id = makeActivityId(ActivityKind.PRICES, 'cancel-signal');

      let release!: () => void;
      const firstStageDone = new Promise<void>((resolve) => {
        release = resolve;
      });
      const secondStage = vi.fn();

      const outcome = submitTask({
        id,
        kind: ActivityKind.PRICES,
        run: async ({ cancelled }): ResultAsync<void, TaskError> => {
          await firstStageDone;
          if (cancelled())
            return err(Cancelled({ message: 'stopped between stages' }));

          secondStage();
          return ok(undefined);
        },
        title: 'prices',
      });

      cancelActivity(ActivityKind.PRICES, 'cancel-signal');
      release();
      await outcome;

      // The stage after the cancel never ran.
      expect(secondStage).not.toHaveBeenCalled();
    });

    it('should read false for a body that was never cancelled', async () => {
      const { submitTask } = useNativeTask();
      const seen: boolean[] = [];

      await submitTask({
        id: makeActivityId(ActivityKind.PRICES, 'cancel-signal-clean'),
        kind: ActivityKind.PRICES,
        run: async ({ cancelled }): ResultAsync<void, TaskError> => {
          seen.push(cancelled());
          return ok(undefined);
        },
        title: 'prices',
      });

      expect(seen).toStrictEqual([false]);
    });

    /** A session ending has to reach bodies mid-stage too, or they work on for a logged-out user. */
    it('should tell a running body that the session ended', async () => {
      const { reset, submitTask } = useNativeTask();
      let release!: () => void;
      const firstStageDone = new Promise<void>((resolve) => {
        release = resolve;
      });
      const secondStage = vi.fn();

      const outcome = submitTask({
        id: makeActivityId(ActivityKind.PRICES, 'cancel-signal-reset'),
        kind: ActivityKind.PRICES,
        run: async ({ cancelled }): ResultAsync<void, TaskError> => {
          await firstStageDone;
          if (cancelled())
            return err(Cancelled({ message: 'session ended' }));

          secondStage();
          return ok(undefined);
        },
        title: 'prices',
      });

      reset();
      release();
      await outcome;

      expect(secondStage).not.toHaveBeenCalled();
    });
  });

  describe('supersedeTask', () => {
    const stalls = async (): ResultAsync<void, TaskError> => new Promise<Result<void, TaskError>>(() => {});

    /**
     * `submitTask` dedups, so a user asking for fresh data while a background run is in flight
     * would be handed that run's promise *and its parameters*. Superseding replaces it instead.
     */
    it('should replace a run already in flight', async () => {
      const { submitTask, supersedeTask } = useNativeTask();
      const id = makeActivityId(ActivityKind.PRICES, 'supersede-replaces');

      const background = submitTask({ id, kind: ActivityKind.PRICES, run: stalls, title: 'prices' });

      const run = vi.fn(async () => ok(undefined));
      await supersedeTask({ id, kind: ActivityKind.PRICES, run, title: 'prices' });

      // The new spec actually ran, rather than dedupping onto the stalled one.
      expect(run).toHaveBeenCalledOnce();
      // And the abandoned caller was settled, not stranded.
      await expect(background).resolves.toBeDefined();
    });

    /**
     * The regression this helper exists to prevent. `finish()` is what frees the id, and it runs
     * when the cancelled activity settles — so submitting without awaiting dedups onto the corpse
     * and the new spec never runs. Dropping the `await` in `supersedeTask` fails this.
     */
    it('should not dedup the replacement onto the cancelled run', async () => {
      const { submitTask, supersedeTask } = useNativeTask();
      const id = makeActivityId(ActivityKind.PRICES, 'supersede-frees-id');

      const background = submitTask({ id, kind: ActivityKind.PRICES, run: stalls, title: 'prices' });
      const run = vi.fn(async () => ok(undefined));

      const outcome = await supersedeTask({ id, kind: ActivityKind.PRICES, run, title: 'prices' });

      expect(isOk(outcome)).toBe(true);
      expect(run).toHaveBeenCalledOnce();
      await background;
    });

    it('should just submit when nothing is in flight', async () => {
      const { supersedeTask } = useNativeTask();
      const run = vi.fn(async () => ok(undefined));

      await supersedeTask({
        id: makeActivityId(ActivityKind.PRICES, 'supersede-idle'),
        kind: ActivityKind.PRICES,
        run,
        title: 'prices',
      });

      expect(run).toHaveBeenCalledOnce();
    });
  });

  describe('reset', () => {
    /** Only the orchestrator can settle this, which is the whole point of the two tests below. */

    it('should settle a caller waiting on work that reset dropped, which would poison the id', async () => {
      const { submitTask } = useNativeTask();
      const orchestrator = useTaskOrchestrator();
      const id = makeActivityId(ActivityKind.PRICES, 'reset-settles');

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

    it('should free the activity id on reset, so the same activity runs again instead of dedupping onto the abandoned promise', async () => {
      const { submitTask } = useNativeTask();
      const orchestrator = useTaskOrchestrator();
      const id = makeActivityId(ActivityKind.PRICES, 'reset-reruns');

      const abandoned = submitTask({
        id,
        kind: ActivityKind.PRICES,
        run: neverSettles,
        title: 'prices',
      });

      orchestrator.reset();
      await abandoned;

      const run = vi.fn(async () => ok(undefined));
      await submitTask({ id, kind: ActivityKind.PRICES, run, title: 'prices' });

      expect(run).toHaveBeenCalledOnce();
    });

    it('should start new work after reset even when every lane slot was taken', async () => {
      const { submitTask } = useNativeTask();
      const orchestrator = useTaskOrchestrator();

      const abandoned = [1, 2, 3, 4].map(async n => submitTask({
        id: makeActivityId(ActivityKind.PRICES, `slot-${n}`),
        kind: ActivityKind.PRICES,
        run: neverSettles,
        title: 'prices',
      }));

      orchestrator.reset();
      await Promise.all(abandoned);

      const run = vi.fn(async () => ok(undefined));
      const raced = await Promise.race([
        submitTask({
          id: makeActivityId(ActivityKind.PRICES, 'after-reset'),
          kind: ActivityKind.PRICES,
          run,
          title: 'prices',
        }).then(() => 'settled'),
        new Promise<string>((resolve) => {
          setTimeout(resolve, 50, 'HUNG');
        }),
      ]);

      expect(raced).toBe('settled');
      expect(run).toHaveBeenCalledOnce();
    });
  });
});
