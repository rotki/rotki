import { bigNumberify } from '@rotki/common';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { usePriceApi } from '@/modules/balances/api/use-price-api';

const runTaskMock = vi.fn();

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
      await taskFn();
      return runTaskMock(taskFn, ...rest);
    },
    cancelTask: vi.fn(),
    cancelTaskByTaskType: vi.fn(),
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({
    notifyError: vi.fn(),
  })),
}));

/** Exceeds CACHE_EXPIRY (10 min) from item-cache.ts to ensure cache invalidation */
const PAST_CACHE_EXPIRY_MS = 1000 * 60 * 11;

describe('useHistoricPriceCache', () => {
  let useHistoricPriceCache: typeof import('@/modules/assets/prices/use-historic-price-cache').useHistoricPriceCache;

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.resetModules();
    setActivePinia(createPinia());
    const mod = await import('@/modules/assets/prices/use-historic-price-cache');
    useHistoricPriceCache = mod.useHistoricPriceCache;
    vi.mocked(usePriceApi().queryHistoricalRates).mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const mockAsset = 'ETH';
  const mockTimestamp = 1730044800;
  const mockPrice = 1000;

  it('should cache price', async () => {
    const { createKey, resolve } = useHistoricPriceCache();
    const key = createKey(mockAsset, mockTimestamp);
    const mockPricesResponse = {
      targetAsset: 'USD',
      assets: {
        [mockAsset]: {
          [mockTimestamp]: mockPrice,
        },
      },
    };
    runTaskMock.mockResolvedValue({ success: true, result: mockPricesResponse });
    resolve(key);
    resolve(key);
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();
    expect(resolve(key)).toEqual(bigNumberify(mockPrice));
  });

  it('should not request failed assets twice unless they expire', async () => {
    runTaskMock.mockResolvedValue({
      success: true,
      result: {
        targetAsset: 'USD',
        assets: {},
      },
    });
    const { createKey, resolve } = useHistoricPriceCache();
    const key = createKey(mockAsset, mockTimestamp);
    resolve(key);
    resolve(key);
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();
    expect(resolve(key)).toBeNull();
    vi.advanceTimersByTime(PAST_CACHE_EXPIRY_MS);
    resolve(key);
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(resolve(key)).toBeNull();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledTimes(2);
  });

  it('should only re-request asset if cache entry expires', async () => {
    const { createKey, resolve } = useHistoricPriceCache();
    const key = createKey(mockAsset, mockTimestamp);
    const mockPricesResponse = {
      targetAsset: 'USD',
      assets: {
        [mockAsset]: {
          [mockTimestamp]: mockPrice,
        },
      },
    };
    runTaskMock.mockResolvedValue({ success: true, result: mockPricesResponse });

    resolve(key);
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();
    expect(resolve(key)).toEqual(bigNumberify(mockPrice));
    vi.advanceTimersByTime(PAST_CACHE_EXPIRY_MS);
    resolve(key);
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledTimes(2);
    expect(resolve(key)).toEqual(bigNumberify(mockPrice));
  });

  it('should store resolved prices in the shared store storage', async () => {
    const { createKey, resolve } = useHistoricPriceCache();
    const { useHistoricCachePriceStore } = await import('@/modules/assets/prices/use-historic-cache-price-store');
    const { historicStorage } = useHistoricCachePriceStore();
    const key = createKey(mockAsset, mockTimestamp);

    runTaskMock.mockResolvedValue({
      success: true,
      result: {
        targetAsset: 'USD',
        assets: { [mockAsset]: { [mockTimestamp]: mockPrice } },
      },
    });

    resolve(key);
    vi.advanceTimersByTime(2500);
    await flushPromises();

    // The cache lives in the app-lifetime store, not a composable-scoped map, so
    // the store's storage must hold the resolved value.
    expect(get(historicStorage.cache)[key]).toEqual(bigNumberify(mockPrice));
  });

  it('should retain cached prices after the composable is torn down and re-created', async () => {
    const key = `${mockAsset}#${mockTimestamp}`;
    runTaskMock.mockResolvedValue({
      success: true,
      result: {
        targetAsset: 'USD',
        assets: { [mockAsset]: { [mockTimestamp]: mockPrice } },
      },
    });

    // First subscriber resolves and populates the store-backed cache.
    const scope1 = effectScope();
    let first!: ReturnType<typeof useHistoricPriceCache>;
    scope1.run(() => {
      first = useHistoricPriceCache();
    });
    first.resolve(key);
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(first.resolve(key)).toEqual(bigNumberify(mockPrice));
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();

    // Last subscriber unmounts -> createSharedComposable disposes the instance.
    scope1.stop();

    // A new subscriber re-creates the composable; the cache must come back from
    // the store with no refetch.
    const scope2 = effectScope();
    let second!: ReturnType<typeof useHistoricPriceCache>;
    scope2.run(() => {
      second = useHistoricPriceCache();
    });
    // Confirm the shared instance was actually disposed and re-created.
    expect(second).not.toBe(first);
    expect(get(second.cache)[key]).toEqual(bigNumberify(mockPrice));
    expect(second.resolve(key)).toEqual(bigNumberify(mockPrice));
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();
    scope2.stop();
  });

  it('should reset historical prices data', async () => {
    const { cache, createKey, resetHistoricalPricesData, resolve } = useHistoricPriceCache();

    // Under range (should be removed alongside with the targeted timestamp)
    const mockTimestamp1 = mockTimestamp - (59 * 60);
    const mockTimestamp2 = mockTimestamp + (59 * 60);
    const key = createKey(mockAsset, mockTimestamp);
    const key1 = createKey(mockAsset, mockTimestamp1);
    const key2 = createKey(mockAsset, mockTimestamp2);

    // Outside range (should not be removed)
    const mockTimestamp3 = mockTimestamp - (100 * 60);
    const mockTimestamp4 = mockTimestamp + (100 * 60);
    const key3 = createKey(mockAsset, mockTimestamp3);
    const key4 = createKey(mockAsset, mockTimestamp4);

    // Other asset, but under range (should not be removed)
    const otherKey = createKey('OTHER', mockTimestamp1);

    const mockPricesResponse = {
      targetAsset: 'USD',
      assets: {
        [mockAsset]: {
          [mockTimestamp]: mockPrice,
          [mockTimestamp1]: mockPrice,
          [mockTimestamp2]: mockPrice,
          [mockTimestamp3]: mockPrice,
          [mockTimestamp4]: mockPrice,
        },
        OTHER: {
          [mockTimestamp1]: mockPrice,
        },
      },
    };
    runTaskMock.mockResolvedValue({ success: true, result: mockPricesResponse });

    resolve(key);
    resolve(key1);
    resolve(key2);
    resolve(key3);
    resolve(key4);
    resolve(otherKey);

    vi.advanceTimersByTime(2500);
    await flushPromises();

    let entries = Object.entries(get(cache));
    expect(entries).toHaveLength(6);

    resetHistoricalPricesData([
      { fromAsset: mockAsset, timestamp: mockTimestamp },
    ]);

    entries = Object.entries(get(cache));
    expect(entries).toHaveLength(3);

    expect(entries.map(([id]) => id)).toContain(key3);
    expect(entries.map(([id]) => id)).toContain(key4);
    expect(entries.map(([id]) => id)).toContain(otherKey);

    expect(entries.map(([id]) => id)).not.toContain(key);
    expect(entries.map(([id]) => id)).not.toContain(key1);
    expect(entries.map(([id]) => id)).not.toContain(key2);
  });
});
