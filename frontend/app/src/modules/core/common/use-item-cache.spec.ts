import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { watchSyncEffect } from 'vue';
import { logger } from '@/modules/core/common/logging/logging';
import { createItemCache, createItemCacheStorage } from '@/modules/core/common/use-item-cache';

interface TestEntry {
  key: string;
  item: string | null;
}

function createMockFetch(
  results: Record<string, string | null>,
): { fetch: (keys: string[]) => Promise<() => IterableIterator<TestEntry>>; calls: string[][] } {
  const calls: string[][] = [];
  const fetch = async (keys: string[]): Promise<() => IterableIterator<TestEntry>> => {
    calls.push([...keys]);
    return function* (): Generator<TestEntry, void> {
      for (const key of keys) {
        yield { item: results[key] ?? null, key };
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

  describe('peek', () => {
    it('should return a cached value without queueing a fetch', async () => {
      const { fetch } = createMockFetch({ KEY: 'value' });
      const { peek, resolve } = createItemCache(fetch);

      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(peek('KEY')).toBe('value');
    });

    it('should return null and never trigger a fetch for an unknown key', async () => {
      const { calls, fetch } = createMockFetch({ KEY: 'value' });
      const { peek } = createItemCache(fetch);

      expect(peek('KEY')).toBeNull();

      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(0);
      expect(peek('KEY')).toBeNull();
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

  describe('storage injection', () => {
    it('should create an empty storage container', () => {
      const storage = createItemCacheStorage<string>();

      expect(get(storage.cache)).toEqual({});
      expect(storage.recent.size).toBe(0);
      expect(storage.unknown.size).toBe(0);
    });

    it('should keep resolved values when a new cache binds to the same storage', async () => {
      const storage = createItemCacheStorage<string>();
      const { calls, fetch } = createMockFetch({ KEY: 'value' });

      // First cache instance resolves and populates the shared storage.
      const first = createItemCache(fetch, { storage });
      first.resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(first.resolve('KEY')).toBe('value');
      expect(calls).toHaveLength(1);

      // Simulate composable teardown + re-init: a brand new cache instance binds
      // to the SAME storage. The value must already be there with no refetch.
      const second = createItemCache(fetch, { storage });
      expect(second.resolve('KEY')).toBe('value');

      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(1);
    });

    it('should preserve the unknown (negative) cache across re-init', async () => {
      const storage = createItemCacheStorage<string>();
      const { calls, fetch } = createMockFetch({ KEY: null });

      const first = createItemCache(fetch, { storage });
      first.resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(storage.unknown.has('KEY')).toBe(true);
      expect(calls).toHaveLength(1);

      // New instance on the same storage must not re-fetch a known-unknown key.
      const second = createItemCache(fetch, { storage });
      expect(second.resolve('KEY')).toBeNull();
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(1);
    });

    it('should start empty (and refetch) when no shared storage is provided', async () => {
      const { calls, fetch } = createMockFetch({ KEY: 'value' });

      const first = createItemCache(fetch);
      first.resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();
      expect(calls).toHaveLength(1);

      // Without injected storage each instance owns its own cache, so a fresh
      // instance has nothing and must fetch again.
      const second = createItemCache(fetch);
      expect(second.resolve('KEY')).toBeNull();
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(calls).toHaveLength(2);
    });

    it('should reset shared storage when reset is called', async () => {
      const storage = createItemCacheStorage<string>();
      const { fetch } = createMockFetch({ KEY: 'value' });

      const first = createItemCache(fetch, { storage });
      first.resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(get(storage.cache).KEY).toBe('value');

      first.reset();

      expect(Object.keys(get(storage.cache))).toHaveLength(0);
      expect(storage.recent.size).toBe(0);
      expect(storage.unknown.size).toBe(0);
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

  describe('deleteCacheKey LRU index', () => {
    it('should not leak the key in the LRU index (recent)', async () => {
      const storage = createItemCacheStorage<string>();
      const { fetch } = createMockFetch({ KEY: 'value' });
      const { deleteCacheKey, resolve, size } = createItemCache(fetch, { storage });

      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(size()).toBe(1);
      expect(storage.recent.has('KEY')).toBe(true);

      deleteCacheKey('KEY');

      // The LRU index must shrink too, otherwise phantom entries inflate the
      // size and trigger premature eviction of live keys.
      expect(size()).toBe(0);
      expect(storage.recent.has('KEY')).toBe(false);
    });
  });

  describe('deleteCacheKeys', () => {
    it('should remove many keys with a single reactive notification', async () => {
      const { fetch } = createMockFetch({ A: 'alpha', B: 'beta', C: 'gamma' });
      const { cache, deleteCacheKeys, resolve, size } = createItemCache(fetch);

      resolve('A');
      resolve('B');
      resolve('C');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(size()).toBe(3);

      deleteCacheKeys(['A', 'B']);

      expect(size()).toBe(1);
      expect(get(cache).A).toBeUndefined();
      expect(get(cache).B).toBeUndefined();
      expect(get(cache).C).toBe('gamma');
    });

    it('should be a no-op for an empty list', () => {
      const { fetch } = createMockFetch({});
      const { deleteCacheKeys, size } = createItemCache(fetch);

      expect(() => deleteCacheKeys([])).not.toThrow();
      expect(size()).toBe(0);
    });
  });

  describe('resilient capacity', () => {
    it('should grow past the soft cap without evicting', async () => {
      const { fetch } = createMockFetch({ A: 'a', B: 'b', C: 'c', D: 'd', E: 'e' });
      const { cache, resolve, size } = createItemCache(fetch, { maxSize: 10, size: 2 });

      for (const key of ['A', 'B', 'C', 'D', 'E']) resolve(key);
      vi.advanceTimersByTime(1000);
      await flushPromises();

      // Soft cap is 2 but the working set of 5 fits under the hard cap of 10.
      expect(size()).toBe(5);
      expect(get(cache).A).toBe('a');
      expect(get(cache).E).toBe('e');
    });

    it('should reclaim expired entries before growing further', async () => {
      const { fetch } = createMockFetch({ A: 'a', B: 'b', C: 'c' });
      const { cache, resolve, size } = createItemCache(fetch, { expiry: 1000, maxSize: 10, size: 2 });

      resolve('A');
      resolve('B');
      vi.advanceTimersByTime(1000);
      await flushPromises();
      expect(size()).toBe(2);

      // Let A and B age out (nothing reads them, so their expiry lapses).
      vi.advanceTimersByTime(5000);

      resolve('C');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      // Inserting C at the soft cap reclaims the two expired entries first.
      expect(size()).toBe(1);
      expect(get(cache).C).toBe('c');
      expect(get(cache).A).toBeUndefined();
      expect(get(cache).B).toBeUndefined();
    });

    it('should force-evict the oldest live entry and warn at the hard cap', async () => {
      const warnSpy = vi.spyOn(logger, 'warn').mockImplementation(() => {});
      const { fetch } = createMockFetch({ A: 'a', B: 'b', C: 'c', D: 'd', E: 'e' });
      // expiry huge so nothing is reclaimable — every entry stays live.
      const { cache, resolve, size } = createItemCache(fetch, { expiry: 1_000_000, label: 'test', maxSize: 3, size: 2 });

      for (const key of ['A', 'B', 'C', 'D', 'E']) resolve(key);
      vi.advanceTimersByTime(1000);
      await flushPromises();

      // Held at the hard cap; the two oldest (A, B) were force-evicted.
      expect(size()).toBe(3);
      expect(get(cache).A).toBeUndefined();
      expect(get(cache).B).toBeUndefined();
      expect(get(cache).E).toBe('e');
      // The warning is throttled to once per window even across multiple evictions.
      expect(warnSpy).toHaveBeenCalledTimes(1);
      expect(warnSpy.mock.calls[0][0]).toContain('test');
      warnSpy.mockRestore();
    });

    it('should keep maxSize at least the soft cap when configured lower', async () => {
      const { fetch } = createMockFetch({ A: 'a', B: 'b', C: 'c' });
      const { resolve, size } = createItemCache(fetch, { expiry: 1_000_000, maxSize: 1, size: 3 });

      for (const key of ['A', 'B', 'C']) resolve(key);
      vi.advanceTimersByTime(1000);
      await flushPromises();

      // maxSize (1) is clamped up to size (3), so all three fit.
      expect(size()).toBe(3);
    });
  });

  describe('refresh ordering', () => {
    it('should move the refreshed key to the most-recent end of the LRU', async () => {
      const storage = createItemCacheStorage<string>();
      const { fetch } = createMockFetch({ A: 'a', B: 'b' });
      const { refresh, resolve } = createItemCache(fetch, { storage });

      resolve('A');
      resolve('B');
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect([...storage.recent.keys()]).toEqual(['A', 'B']);

      refresh('A');

      // A must jump to the end; an in-place set would leave it stale at the front
      // and break both LRU recency and the expiry-ordering the sweep relies on.
      expect([...storage.recent.keys()]).toEqual(['B', 'A']);
    });
  });

  describe('unknown map bounding', () => {
    it('should keep the negative cache under the hard cap', async () => {
      const { fetch } = createMockFetch({});
      const { resolve, unknown } = createItemCache(fetch, { maxSize: 2, size: 1 });

      for (const key of ['A', 'B', 'C', 'D']) resolve(key);
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(unknown.size).toBeLessThanOrEqual(2);
    });
  });

  describe('error backoff', () => {
    it('should hold failed keys back before retrying', async () => {
      vi.spyOn(logger, 'error').mockImplementation(() => {});
      const calls: string[][] = [];
      const fetch = async (keys: string[]): Promise<() => IterableIterator<{ key: string; item: string }>> => {
        calls.push([...keys]);
        throw new Error('backend down');
      };
      const { resolve } = createItemCache(fetch);

      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();
      expect(calls).toHaveLength(1);

      // Within the backoff window a re-request must not fire another fetch.
      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();
      expect(calls).toHaveLength(1);

      // After the backoff window it retries.
      vi.advanceTimersByTime(5000);
      resolve('KEY');
      vi.advanceTimersByTime(1000);
      await flushPromises();
      expect(calls).toHaveLength(2);
    });
  });

  describe('fine-grained reactivity', () => {
    it('should re-run a reader when its own key resolves', async () => {
      const { fetch } = createMockFetch({ KEY: 'value' });
      const { resolve } = createItemCache(fetch);

      let runs = 0;
      let last: string | null = null;
      const stop = watchSyncEffect(() => {
        runs++;
        last = resolve('KEY');
      });

      const runsBefore = runs;
      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(runs).toBeGreaterThan(runsBefore);
      expect(last).toBe('value');
      stop();
    });

    it('should not re-run a reader of one key when an unrelated key resolves', async () => {
      const { fetch } = createMockFetch({ A: 'a', B: 'b' });
      const { resolve } = createItemCache(fetch);

      let aRuns = 0;
      const stopA = watchSyncEffect(() => {
        aRuns++;
        resolve('A');
      });
      vi.advanceTimersByTime(1000);
      await flushPromises();

      // A has resolved; snapshot its run count.
      const aRunsAfterA = aRuns;
      expect(resolve('A')).toBe('a');

      // Now resolve B through a separate reader.
      let bRuns = 0;
      const stopB = watchSyncEffect(() => {
        bRuns++;
        resolve('B');
      });
      vi.advanceTimersByTime(1000);
      await flushPromises();

      // B's reader re-ran for B's own resolution...
      expect(bRuns).toBeGreaterThan(1);
      expect(resolve('B')).toBe('b');
      // ...but A's reader must NOT have re-run: with a single coarse ref it would have.
      expect(aRuns).toBe(aRunsAfterA);
      stopA();
      stopB();
    });

    it('should re-run a reader that early-returns on pending once the value arrives', async () => {
      const { fetch } = createMockFetch({ KEY: 'value' });
      const { getIsPending, resolve } = createItemCache(fetch);

      const seen: (string | null)[] = [];
      const stop = watchSyncEffect(() => {
        // A consumer that never reads the value while pending (like getHistoricPrice)
        // must still be subscribed so it re-runs when the value lands.
        if (getIsPending('KEY')) {
          seen.push('PENDING');
          return;
        }
        seen.push(resolve('KEY'));
      });

      vi.advanceTimersByTime(1000);
      await flushPromises();

      expect(seen).toContain('PENDING');
      expect(seen.at(-1)).toBe('value');
      stop();
    });
  });
});
