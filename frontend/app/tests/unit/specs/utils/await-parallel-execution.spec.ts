import { describe, expect, it, vi } from 'vitest';

describe('awaitParallelExecution', () => {
  it('instant resolve if no items exist', async () => {
    await expect(
      awaitParallelExecution<{ id: string }>(
        [],
        id => id.id,
        () => Promise.resolve(),
      ),
    ).resolves.toBeUndefined();
  });

  it('resolves after all promises resolve', async () => {
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
});
