import type { BigNumber } from '@rotki/common';
import { usePriceApi } from '@/composables/api/balances/price';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useTaskStore } from '@/store/tasks';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    isTaskRunning: vi.fn().mockReturnValue(false),
    awaitTask: vi.fn().mockResolvedValue({}),
  }),
}));

describe('store::prices/historic', () => {
  let store: ReturnType<typeof useHistoricCachePriceStore>;

  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    store = useHistoricCachePriceStore();
    vi.mocked(usePriceApi().queryHistoricalRates).mockClear();
  });

  const mockAsset = 'ETH';
  const mockTimestamp = 1730044800;
  const mockPrice = 1000;

  it('should cache price', async () => {
    const { createKey } = store;
    const key = createKey(mockAsset, mockTimestamp);
    const mockPricesResponse = {
      targetAsset: 'USD',
      assets: {
        [mockAsset]: {
          [mockTimestamp]: mockPrice,
        },
      },
    };
    vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
      result: mockPricesResponse,
      meta: { title: '' },
    });
    const firstRetrieval: ComputedRef<BigNumber | null> = store.retrieve(key);
    const secondRetrieval: ComputedRef<BigNumber | null> = store.retrieve(key);
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();
    expect(get(firstRetrieval)).toEqual(bigNumberify(mockPrice));
    expect(get(secondRetrieval)).toEqual(bigNumberify(mockPrice));
  });

  it('should not request failed assets twice unless they expire', async () => {
    vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
      result: {
        targetAsset: 'USD',
        assets: {},
      },
      meta: { title: '' },
    });
    const { createKey } = store;
    const key = createKey(mockAsset, mockTimestamp);
    const firstRetrieval: ComputedRef<BigNumber | null> = store.retrieve(key);
    const secondRetrieval: ComputedRef<BigNumber | null> = store.retrieve(key);
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();
    expect(get(firstRetrieval)).toBeNull();
    expect(get(secondRetrieval)).toBeNull();
    vi.advanceTimersByTime(1000 * 60 * 11);
    const thirdRetrieval: ComputedRef<BigNumber | null> = store.retrieve(key);
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(get(thirdRetrieval)).toBeNull();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledTimes(2);
  });

  it('should only re-request asset if cache entry expires', async () => {
    const { createKey } = store;
    const key = createKey(mockAsset, mockTimestamp);
    const mockPricesResponse = {
      targetAsset: 'USD',
      assets: {
        [mockAsset]: {
          [mockTimestamp]: mockPrice,
        },
      },
    };
    vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
      result: mockPricesResponse,
      meta: { title: '' },
    });

    const firstRetrieval: ComputedRef<BigNumber | null> = store.retrieve(key);
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();
    expect(get(firstRetrieval)).toEqual(bigNumberify(mockPrice));
    vi.advanceTimersByTime(1000 * 60 * 11);
    const secondRetrieval: ComputedRef<BigNumber | null> = store.retrieve(key);
    vi.advanceTimersToNextTimer();
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledTimes(2);
    expect(get(secondRetrieval)).toEqual(bigNumberify(mockPrice));
  });

  it('resetHistoricalPricesData', async () => {
    const { createKey } = store;
    const key = createKey(mockAsset, mockTimestamp);

    // Under range (should be removed alongside with the targeted timestamp)
    const mockTimestamp1 = mockTimestamp - (59 * 60);
    const mockTimestamp2 = mockTimestamp + (59 * 60);
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
    vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
      result: mockPricesResponse,
      meta: { title: '' },
    });

    store.retrieve(key);
    store.retrieve(key1);
    store.retrieve(key2);
    store.retrieve(key3);
    store.retrieve(key4);
    store.retrieve(otherKey);

    vi.advanceTimersByTime(2500);
    await flushPromises();

    let entries = Object.entries(get(store.cache));
    expect(entries).toHaveLength(6);

    store.resetHistoricalPricesData([
      { fromAsset: mockAsset, timestamp: mockTimestamp },
    ]);

    entries = Object.entries(get(store.cache));
    expect(entries).toHaveLength(3);

    expect(entries.map(([id]) => id)).toContain(key3);
    expect(entries.map(([id]) => id)).toContain(key4);
    expect(entries.map(([id]) => id)).toContain(otherKey);

    expect(entries.map(([id]) => id)).not.toContain(key);
    expect(entries.map(([id]) => id)).not.toContain(key1);
    expect(entries.map(([id]) => id)).not.toContain(key2);
  });
});
