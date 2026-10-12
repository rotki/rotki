import { withSetup } from '@test/utils/with-setup';
import { describe, expect, it, vi } from 'vitest';
import { useStakingRows } from '@/modules/staking/use-staking-rows';

function setup(fetch: () => Promise<string[]>): ReturnType<typeof useStakingRows<string[], string, number>> {
  return withSetup(() => useStakingRows<string[], string, number>({
    fetch,
    toRows: response => response,
    toTotal: rows => rows.length,
  })).result;
}

describe('modules/staking/useStakingRows', () => {
  it('should expose the rows of the response and the total derived from them', async () => {
    const result = setup(vi.fn<() => Promise<string[]>>().mockResolvedValue(['a', 'b']));

    await result.refresh();

    expect(get(result.rows)).toEqual(['a', 'b']);
    expect(get(result.total)).toBe(2);
  });

  it('should report a failed query and keep the rows of the last successful one', async () => {
    const fetch = vi.fn<() => Promise<string[]>>()
      .mockResolvedValueOnce(['a'])
      .mockRejectedValueOnce(new Error('api down'));
    const result = setup(fetch);

    await result.refresh();
    await result.refresh();

    expect(get(result.error)).toBe('api down');
    expect(get(result.rows)).toEqual(['a']);
  });

  it('should clear a previous error once a query succeeds', async () => {
    const fetch = vi.fn<() => Promise<string[]>>()
      .mockRejectedValueOnce(new Error('api down'))
      .mockResolvedValueOnce([]);
    const result = setup(fetch);

    await result.refresh();
    await result.refresh();

    expect(get(result.error)).toBe('');
  });

  it('should be loading only while a query is in flight', async () => {
    const result = setup(vi.fn<() => Promise<string[]>>().mockResolvedValue([]));

    const pending = result.refresh();
    expect(get(result.loading)).toBe(true);

    await pending;
    expect(get(result.loading)).toBe(false);
  });
});
