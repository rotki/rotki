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

  it('should settle the umbrella activity itself, a tick after its own promise resolves', async () => {
    const { runActivityBatch } = useActivityBatch();
    const { statusOf } = useTaskOrchestrator();

    await runActivityBatch(umbrella(), ['a'], async item => item);

    await vi.waitFor(() => {
      expect(statusOf(ActivityKind.ACCOUNTS, 'add', 'eth', 'batch').active).toBe(false);
    });
  });
});
