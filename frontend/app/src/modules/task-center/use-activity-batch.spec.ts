import type { ResultAsync } from 'plainfp/result-async';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { ok, type Result } from 'plainfp/result';
import { describe, expect, it, vi } from 'vitest';
import { Priority } from '@/modules/task-center/core/orchestrator/spec';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useActivityBatch } from '@/modules/task-center/use-activity-batch';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  useTaskHandler: (): Record<string, unknown> => ({
    cancelTaskById: vi.fn(async () => true),
    runTaskResult: vi.fn(),
  }),
}));

const umbrellaId = makeActivityId(ActivityKind.ACCOUNTS, 'add', 'eth', 'batch');

function umbrella(): { id: typeof umbrellaId; kind: ActivityKind; title: string } {
  return { id: umbrellaId, kind: ActivityKind.ACCOUNTS, title: 'accounts' };
}

describe('useActivityBatch', () => {
  it('should run every item and return the results in order', async () => {
    const { runActivityBatch } = useActivityBatch();
    const results = await runActivityBatch(umbrella(), ['a', 'b', 'c'], async item => item.toUpperCase());

    expect(results).toStrictEqual(['A', 'B', 'C']);
  });

  it('should give every child the umbrella as its parent', async () => {
    const { runActivityBatch } = useActivityBatch();
    const parents: (string | undefined)[] = [];

    await runActivityBatch(umbrella(), ['a', 'b'], async (_item, parent) => {
      parents.push(parent);
    });

    expect(parents).toStrictEqual([umbrellaId, umbrellaId]);
  });

  it('should submit no umbrella for a single item, which it would only describe twice', async () => {
    const { runActivityBatch } = useActivityBatch();
    const { statusOf } = useTaskOrchestrator();
    const parents: (string | undefined)[] = [];
    const soleId = makeActivityId(ActivityKind.ACCOUNTS, 'add', 'sole', 'batch');

    const results = await runActivityBatch({ ...umbrella(), id: soleId }, ['only'], async (item, parent) => {
      parents.push(parent);
      return item;
    });

    expect(results).toStrictEqual(['only']);
    expect(parents).toStrictEqual([undefined]);
    expect(statusOf(ActivityKind.ACCOUNTS, 'add', 'sole', 'batch').everCompleted).toBe(false);
  });

  it('should submit no umbrella for an empty batch', async () => {
    const { runActivityBatch } = useActivityBatch();
    const run = vi.fn();

    expect(await runActivityBatch(umbrella(), [], run)).toStrictEqual([]);
    expect(run).not.toHaveBeenCalled();
  });

  it('should still settle when one item rejects, the failure belonging to that item', async () => {
    const { runActivityBatch } = useActivityBatch();
    const seen: string[] = [];

    const results = runActivityBatch(umbrella(), ['a', 'b', 'c'], async (item) => {
      if (item === 'a')
        throw new Error('boom');

      seen.push(item);
      return item;
    });

    await expect(results).rejects.toThrow('boom');
    expect(seen).toStrictEqual(['b', 'c']);
  });

  it('should let a user-priority umbrella through the balance pause of a running history sync', async () => {
    const { runActivityBatch } = useActivityBatch();
    const { statusOf, submit } = useTaskOrchestrator();
    let finishSync!: () => void;
    submit({
      id: makeActivityId(ActivityKind.HISTORY_SYNC, 'batch-spec'),
      kind: ActivityKind.HISTORY_SYNC,
      run: async (): ResultAsync<void, TaskError> => new Promise<Result<void, TaskError>>((resolve) => {
        finishSync = (): void => resolve(ok(undefined));
      }),
      title: 'sync',
    });
    const refreshId = makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'batch-spec');

    try {
      await runActivityBatch({ id: refreshId, kind: ActivityKind.BLOCKCHAIN_BALANCES, priority: Priority.USER, title: 'balances' }, ['eth', 'btc'], async item => item);

      await vi.waitFor(() => {
        expect(statusOf(ActivityKind.BLOCKCHAIN_BALANCES, 'batch-spec').active).toBe(false);
      });
    }
    finally {
      finishSync();
    }
  });

  describe('follow-up', () => {
    /**
     * An activity whose run waits until `release` is called, and records when it started.
     *
     * @remarks
     * `settled` is read off the record's status, so it also resolves when a reset or a cancel
     * settles the record without the run ever being released.
     */
    function heldActivity(name: string, deps: string[] = []): {
      release: () => void;
      settled: Promise<unknown>;
      started: () => boolean;
    } {
      const { statusOf, submit } = useTaskOrchestrator();
      const id = makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'follow-up-spec', name);
      let release!: () => void;
      let started = false;
      submit({
        deps: deps.map(dep => makeActivityId(ActivityKind.BLOCKCHAIN_BALANCES, 'follow-up-spec', dep)),
        id,
        kind: ActivityKind.BLOCKCHAIN_BALANCES,
        run: async (): ResultAsync<void, TaskError> => {
          started = true;
          return new Promise<Result<void, TaskError>>((resolve) => {
            release = (): void => resolve(ok(undefined));
          });
        },
        title: name,
      });
      const settled = vi.waitFor(() => {
        expect(statusOf(ActivityKind.BLOCKCHAIN_BALANCES, 'follow-up-spec', name).active).toBe(false);
      }, { interval: 5, timeout: 2000 });
      return { release: () => release?.(), settled, started: () => started };
    }

    function batchUmbrella(name: string): { id: ReturnType<typeof makeActivityId>; kind: ActivityKind; title: string } {
      return { id: makeActivityId(ActivityKind.ACCOUNTS, name), kind: ActivityKind.ACCOUNTS, title: name };
    }

    it('should declare the follow-up after the items, in the same tick, under the umbrella', async () => {
      const { runActivityBatch } = useActivityBatch();
      const order: string[] = [];
      const parents: (string | undefined)[] = [];

      const running = runActivityBatch(umbrella(), ['a', 'b'], async (item) => {
        order.push(item);
      }, async (parent) => {
        order.push('follow-up');
        parents.push(parent);
      });

      expect(order).toStrictEqual(['a', 'b', 'follow-up']);
      expect(parents).toStrictEqual([umbrellaId]);
      await running;
    });

    it('should hand a one-item batch\'s follow-up the umbrella\'s own parent', async () => {
      const { runActivityBatch } = useActivityBatch();
      const outer = makeActivityId(ActivityKind.ACCOUNTS, 'outer');
      const followUp = vi.fn<(parent: string | undefined) => Promise<void>>(async () => {});

      await runActivityBatch({ ...umbrella(), parent: outer }, ['only'], async item => item, followUp);

      expect(followUp).toHaveBeenCalledExactlyOnceWith(outer);
    });

    it('should start a follow-up that depends on the items only once every item settled', async () => {
      const { runActivityBatch } = useActivityBatch();
      const { statusOf } = useTaskOrchestrator();
      const items: ReturnType<typeof heldActivity>[] = [];
      let node!: ReturnType<typeof heldActivity>;

      const running = runActivityBatch(batchUmbrella('order'), ['a', 'b'], async (item) => {
        const held = heldActivity(`order-${item}`);
        items.push(held);
        await held.settled;
      }, async () => {
        node = heldActivity('order-node', ['order-a', 'order-b']);
        await node.settled;
      });

      await vi.waitFor(() => expect(items.every(item => item.started())).toBe(true));
      items[0].release();
      await items[0].settled;
      await vi.waitFor(() => expect(statusOf(ActivityKind.BLOCKCHAIN_BALANCES, 'follow-up-spec', 'order-a').active).toBe(false));
      expect(node.started()).toBe(false);

      items[1].release();
      await vi.waitFor(() => expect(node.started()).toBe(true));
      node.release();
      await running;
    });

    it('should keep the umbrella open until the follow-up settles', async () => {
      const { runActivityBatch } = useActivityBatch();
      const { statusOf } = useTaskOrchestrator();
      let node!: ReturnType<typeof heldActivity>;

      const running = runActivityBatch(batchUmbrella('open'), ['a', 'b'], async item => item, async () => {
        node = heldActivity('open-node');
        await node.settled;
      });

      await vi.waitFor(() => expect(node.started()).toBe(true));
      expect(statusOf(ActivityKind.ACCOUNTS, 'open').active).toBe(true);

      node.release();
      await running;
      await vi.waitFor(() => expect(statusOf(ActivityKind.ACCOUNTS, 'open').active).toBe(false));
    });

    it('should never run a follow-up that a reset drops while it waits on the items', async () => {
      const { runActivityBatch } = useActivityBatch();
      const { reset } = useTaskOrchestrator();
      const items: ReturnType<typeof heldActivity>[] = [];
      let node!: ReturnType<typeof heldActivity>;

      const running = runActivityBatch(batchUmbrella('reset'), ['a', 'b'], async (item) => {
        const held = heldActivity(`reset-${item}`);
        items.push(held);
        await held.settled;
      }, async () => {
        node = heldActivity('reset-node', ['reset-a', 'reset-b']);
        await node.settled;
      });

      await vi.waitFor(() => expect(items.every(item => item.started())).toBe(true));
      reset();
      await running;

      expect(node.started()).toBe(false);
    });
  });

  it('should settle the umbrella activity itself, a tick after its own promise resolves', async () => {
    const { runActivityBatch } = useActivityBatch();
    const { statusOf } = useTaskOrchestrator();

    await runActivityBatch(umbrella(), ['a'], async item => item);

    await vi.waitFor(() => {
      expect(statusOf(ActivityKind.ACCOUNTS, 'add', 'eth', 'batch').active).toBe(false);
    });
  });
});
