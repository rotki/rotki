import { describe, expect, it, vi } from 'vitest';
import { awaitParallelExecution } from '@/modules/core/common/async/await-parallel-execution';

describe('await-parallel-execution', () => {
  it('should resolve instantly if no items exist', async () => {
    await expect(
      awaitParallelExecution<{ id: string }>(
        [],
        id => id.id,
        async () => Promise.resolve(),
      ),
    ).resolves.toBeUndefined();
  });

  it('should resolve after all promises resolve', async () => {
    const items = 10;
    const p1 = vi.fn();
    await expect(
      awaitParallelExecution<{ id: string }>(
        Array.from({ length: items }, (_, i) => ({
          id: (i + 1).toString(),
        })),
        id => id.id,
        item => p1(item.id),
      ),
    ).resolves.toBeUndefined();
    expect(p1).toHaveBeenCalledTimes(10);
  });

  // The promise only ever resolved through `onCompletion`, and a rejected task skipped the
  // bookkeeping that fires it: the slot was never freed, no queued task started, and the caller
  // waited forever. The CSV import reached this whenever one account addition threw.
  it('should still resolve when a task rejects, and run the remaining items', async () => {
    const seen: string[] = [];
    const run = awaitParallelExecution<{ id: string }>(
      Array.from({ length: 6 }, (_, i) => ({ id: (i + 1).toString() })),
      item => item.id,
      async (item) => {
        if (item.id === '1')
          throw new Error('boom');

        seen.push(item.id);
      },
      2,
    );

    await expect(run).resolves.toBeUndefined();
    expect(seen).toHaveLength(5);
  });
});
