import { describe, expect, it, vi } from 'vitest';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useActivityBatch } from '@/modules/task-center/use-activity-batch';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

// The orchestrator stays real; only the backend runner behind it is stubbed.
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

  // One child needs no parent: an umbrella over a single activity is a second row describing the
  // same work. This is what lets callers stop branching on the item count themselves.
  it('should submit no umbrella for a single item', async () => {
    const { runActivityBatch } = useActivityBatch();
    const { statusOf } = useTaskOrchestrator();
    const parents: (string | undefined)[] = [];
    // Its own id: the orchestrator is a shared singleton, so an umbrella another test in this file
    // already completed would make "no umbrella was submitted" read as false.
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

  // allSettled, not all: the umbrella must not abandon the rest of the batch because one item
  // failed, and it settles complete either way — a failure belongs to the item that failed.
  it('should still settle when one item rejects', async () => {
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

  // `await runActivityBatch(...)` resolves when the umbrella's own promise settles, which is a
  // tick before the orchestrator records the activity terminal. Asserting straight after the await
  // reads it as still active — the same settle lag the task centre shows in the panel.
  it('should settle the umbrella activity itself', async () => {
    const { runActivityBatch } = useActivityBatch();
    const { statusOf } = useTaskOrchestrator();

    await runActivityBatch(umbrella(), ['a'], async item => item);

    await vi.waitFor(() => {
      expect(statusOf(ActivityKind.ACCOUNTS, 'add', 'eth', 'batch').active).toBe(false);
    });
  });
});
