import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createItemCache } from '@/modules/core/common/use-item-cache';

interface TestEntry {
  key: string;
  item: string;
}

function createMockFetch(
  results: Record<string, string | null>,
): { fetch: (keys: string[]) => Promise<() => IterableIterator<TestEntry>>; calls: string[][] } {
  const calls: string[][] = [];
  const fetch = async (keys: string[]): Promise<() => IterableIterator<TestEntry>> => {
    calls.push([...keys]);
    return function* (): Generator<TestEntry, void> {
      for (const key of keys) {
        const item = results[key] ?? null;
        if (item !== null) {
          yield { item, key };
        }
        else {
          yield { item: null as unknown as string, key };
        }
      }
    };
  };
  return { calls, fetch };
}

describe('createItemCache', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  describe('resolve', () => {
    it('should return null before fetch completes', () => {
      const { fetch } = createMockFetch({ KEY: 'value' });
      const { resolve } = createItemCache(fetch);

      expect(resolve('KEY')).toBeNull();
    });

    it('should return cached value after fetch completes', async () => {
      const { fetch } = createMockFetch({ KEY: 'value' });
      const { resolve } = createItemCache(fetch);

      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(resolve('KEY')).toBe('value');
    });
  });

  describe('useResolve', () => {
    it('should return a reactive computed that updates after fetch', async () => {
      const { fetch } = createMockFetch({ KEY: 'value' });
      const { useResolve } = createItemCache(fetch);

      const result = useResolve('KEY');
      expect(get(result)).toBeNull();

      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(get(result)).toBe('value');
    });

    it('should accept a reactive key and track the computed value', async () => {
      const { fetch } = createMockFetch({ A: 'alpha', B: 'beta' });
      const { resolve, useResolve } = createItemCache(fetch);
      const key = ref<string>('A');

      const result = useResolve(key);

      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(get(result)).toBe('alpha');

      // Queue B separately since useResolve only queues the initial key
      resolve('B');
      set(key, 'B');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(get(result)).toBe('beta');
    });
  });

  describe('getIsPending and isPending', () => {
    it('should report pending state during fetch', async () => {
      const { fetch } = createMockFetch({ KEY: 'value' });
      const { getIsPending, isPending, resolve } = createItemCache(fetch);

      resolve('KEY');

      const keyPending = isPending('KEY');
      expect(getIsPending('KEY')).toBe(true);
      expect(get(keyPending)).toBe(true);

      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(getIsPending('KEY')).toBe(false);
      expect(get(keyPending)).toBe(false);
    });

    it('should return false for keys never queued', () => {
      const { fetch } = createMockFetch({});
      const { getIsPending, isPending } = createItemCache(fetch);

      const nopePending = isPending('NOPE');
      expect(getIsPending('NOPE')).toBe(false);
      expect(get(nopePending)).toBe(false);
    });
  });

  describe('refresh', () => {
    it('should re-fetch a cached key', async () => {
      const { calls, fetch } = createMockFetch({ KEY: 'value' });
      const { refresh, resolve } = createItemCache(fetch);

      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(1);
      expect(resolve('KEY')).toBe('value');

      refresh('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(2);
      expect(calls[1]).toContain('KEY');
    });

    it('should re-fetch a previously unknown key', async () => {
      const results: Record<string, string | null> = { KEY: null };
      const { calls, fetch } = createMockFetch(results);
      const { refresh, resolve } = createItemCache(fetch);

      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(resolve('KEY')).toBeNull();
      expect(calls).toHaveLength(1);

      // Now make it resolve successfully
      results.KEY = 'found';
      refresh('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(2);
      expect(resolve('KEY')).toBe('found');
    });
  });

  describe('deleteCacheKey', () => {
    it('should remove a key from the cache', async () => {
      const { fetch } = createMockFetch({ KEY: 'value' });
      const { cache, deleteCacheKey, resolve } = createItemCache(fetch);

      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(get(cache).KEY).toBe('value');

      deleteCacheKey('KEY');
      expect(get(cache).KEY).toBeUndefined();
    });

    it('should also remove from unknown map', async () => {
      const { fetch } = createMockFetch({ KEY: null });
      const { deleteCacheKey, resolve, unknown } = createItemCache(fetch);

      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(unknown.has('KEY')).toBe(true);

      deleteCacheKey('KEY');
      expect(unknown.has('KEY')).toBe(false);
    });
  });

  describe('reset', () => {
    it('should clear all cache state', async () => {
      const results: Record<string, string | null> = { A: 'alpha', B: null };
      const { fetch } = createMockFetch(results);
      const { cache, getIsPending, reset, resolve, unknown } = createItemCache(fetch);

      resolve('A');
      resolve('B');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(get(cache).A).toBe('alpha');
      expect(unknown.has('B')).toBe(true);

      reset();

      expect(Object.keys(get(cache))).toHaveLength(0);
      expect(unknown.size).toBe(0);
      expect(getIsPending('A')).toBe(false);
    });
  });

  describe('batch dedup', () => {
    it('should deduplicate keys in the same batch', async () => {
      const { calls, fetch } = createMockFetch({ KEY: 'value' });
      const { resolve } = createItemCache(fetch);

      resolve('KEY');
      resolve('KEY');
      resolve('KEY');

      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(1);
      expect(calls[0]).toEqual(['KEY']);
    });

    it('should batch multiple different keys into a single fetch', async () => {
      const { calls, fetch } = createMockFetch({ A: 'alpha', B: 'beta', C: 'gamma' });
      const { resolve } = createItemCache(fetch);

      resolve('A');
      resolve('B');
      resolve('C');

      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(1);
      expect(calls[0]).toEqual(expect.arrayContaining(['A', 'B', 'C']));
      expect(calls[0]).toHaveLength(3);
    });
  });

  describe('queueIdentifier', () => {
    it('should not re-queue a key that is in the unknown map and not expired', async () => {
      const { calls, fetch } = createMockFetch({ KEY: null });
      const { queueIdentifier } = createItemCache(fetch);

      queueIdentifier('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(1);

      // Try to queue again — should be skipped (unknown not expired)
      queueIdentifier('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(1);
    });

    it('should re-queue an unknown key after its expiry', async () => {
      const { calls, fetch } = createMockFetch({ KEY: null });
      const { queueIdentifier } = createItemCache(fetch, { expiry: 1000 });

      queueIdentifier('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(1);

      // Advance past expiry
      vi.advanceTimersByTime(1500);

      queueIdentifier('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(2);
    });
  });
});
