import { bigNumberify } from '@rotki/common';
import { mockUseNotifications } from '@test/utils/mocks/notifications';
import { mockUseTaskHandler } from '@test/utils/mocks/task-runner';
import flushPromises from 'flush-promises';
import { ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { usePriceApi } from '@/modules/balances/api/use-price-api';

const { runTaskMock } = vi.hoisted(() => ({ runTaskMock: vi.fn() }));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal =>
  mockUseTaskHandler(await importOriginal<Record<string, unknown>>(), { runTask: runTaskMock }));

vi.mock('@/modules/core/notifications/use-notifications', () => mockUseNotifications());

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
    runTaskMock.mockResolvedValue(ok(mockPricesResponse));
    resolve(key);
    resolve(key);
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();
    expect(resolve(key)).toEqual(bigNumberify(mockPrice));
  });

  it('should not request failed assets twice unless they expire', async () => {
    runTaskMock.mockResolvedValue(ok({
      targetAsset: 'USD',
      assets: {},
    }));
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
    runTaskMock.mockResolvedValue(ok(mockPricesResponse));

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

  it('should store resolved prices in the app-lifetime store, not a composable-scoped map', async () => {
    const { createKey, resolve } = useHistoricPriceCache();
    const { useHistoricCachePriceStore } = await import('@/modules/assets/prices/use-historic-cache-price-store');
    const { historicStorage } = useHistoricCachePriceStore();
    const key = createKey(mockAsset, mockTimestamp);

    runTaskMock.mockResolvedValue(ok({
      targetAsset: 'USD',
      assets: { [mockAsset]: { [mockTimestamp]: mockPrice } },
    }));

    resolve(key);
    vi.advanceTimersByTime(2500);
    await flushPromises();

    expect(get(historicStorage.cache)[key]).toEqual(bigNumberify(mockPrice));
  });

  it('should retain cached prices after the composable is torn down and re-created', async () => {
    const key = `${mockAsset}#${mockTimestamp}`;
    runTaskMock.mockResolvedValue(ok({
      targetAsset: 'USD',
      assets: { [mockAsset]: { [mockTimestamp]: mockPrice } },
    }));

    const onlySubscriber = effectScope();
    let beforeTeardown!: ReturnType<typeof useHistoricPriceCache>;
    onlySubscriber.run(() => {
      beforeTeardown = useHistoricPriceCache();
    });
    beforeTeardown.resolve(key);
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(beforeTeardown.resolve(key)).toEqual(bigNumberify(mockPrice));
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();

    onlySubscriber.stop();

    const laterSubscriber = effectScope();
    let afterTeardown!: ReturnType<typeof useHistoricPriceCache>;
    laterSubscriber.run(() => {
      afterTeardown = useHistoricPriceCache();
    });
    expect(afterTeardown).not.toBe(beforeTeardown);
    expect(get(afterTeardown.cache)[key]).toEqual(bigNumberify(mockPrice));
    expect(afterTeardown.resolve(key)).toEqual(bigNumberify(mockPrice));
    vi.advanceTimersByTime(2500);
    await flushPromises();
    expect(usePriceApi().queryHistoricalRates).toHaveBeenCalledOnce();
    laterSubscriber.stop();
  });

  it('should surface each batch as its own native activity, so two never dedup onto one promise', async () => {
    const { ActivityKind, ActivityPart } = await import('@/modules/task-center/core/types');
    const { useTaskOrchestrator } = await import('@/modules/task-center/use-task-orchestrator');
    const orchestrator = useTaskOrchestrator();
    const { createKey, resolve } = useHistoricPriceCache();

    runTaskMock.mockResolvedValue(ok({
      targetAsset: 'USD',
      assets: { [mockAsset]: { [mockTimestamp]: mockPrice } },
    }));

    resolve(createKey(mockAsset, mockTimestamp));
    vi.advanceTimersByTime(2500);
    await flushPromises();

    resolve(createKey('OTHER', mockTimestamp));
    vi.advanceTimersByTime(2500);
    await flushPromises();

    const ids = orchestrator.snapshot()
      .map(activity => activity.id)
      .filter(id => id.startsWith(`${ActivityKind.PRICES}:${ActivityPart.HISTORIC}:${ActivityPart.BATCH}:`));

    expect(ids).toHaveLength(2);
    expect(new Set(ids).size).toBe(2);
    expect(orchestrator.statusOfPrefix(ActivityKind.PRICES, ActivityPart.HISTORIC).everCompleted).toBe(true);
  });

  it('should reset historical prices data', async () => {
    const { cache, createKey, resetHistoricalPricesData, resolve } = useHistoricPriceCache();

    const insideWindow = 59 * 60;
    const outsideWindow = 100 * 60;

    const targeted = mockTimestamp;
    const insideWindowBefore = targeted - insideWindow;
    const insideWindowAfter = targeted + insideWindow;
    const outsideWindowBefore = targeted - outsideWindow;
    const outsideWindowAfter = targeted + outsideWindow;

    const targetedKey = createKey(mockAsset, targeted);
    const insideWindowBeforeKey = createKey(mockAsset, insideWindowBefore);
    const insideWindowAfterKey = createKey(mockAsset, insideWindowAfter);
    const outsideWindowBeforeKey = createKey(mockAsset, outsideWindowBefore);
    const outsideWindowAfterKey = createKey(mockAsset, outsideWindowAfter);
    const otherAssetInsideWindowKey = createKey('OTHER', insideWindowBefore);

    const mockPricesResponse = {
      targetAsset: 'USD',
      assets: {
        [mockAsset]: {
          [targeted]: mockPrice,
          [insideWindowBefore]: mockPrice,
          [insideWindowAfter]: mockPrice,
          [outsideWindowBefore]: mockPrice,
          [outsideWindowAfter]: mockPrice,
        },
        OTHER: {
          [insideWindowBefore]: mockPrice,
        },
      },
    };
    runTaskMock.mockResolvedValue(ok(mockPricesResponse));

    resolve(targetedKey);
    resolve(insideWindowBeforeKey);
    resolve(insideWindowAfterKey);
    resolve(outsideWindowBeforeKey);
    resolve(outsideWindowAfterKey);
    resolve(otherAssetInsideWindowKey);

    vi.advanceTimersByTime(2500);
    await flushPromises();

    let entries = Object.entries(get(cache));
    expect(entries).toHaveLength(6);

    resetHistoricalPricesData([
      { fromAsset: mockAsset, timestamp: targeted },
    ]);

    entries = Object.entries(get(cache));
    expect(entries).toHaveLength(3);

    expect(entries.map(([id]) => id)).toContain(outsideWindowBeforeKey);
    expect(entries.map(([id]) => id)).toContain(outsideWindowAfterKey);
    expect(entries.map(([id]) => id)).toContain(otherAssetInsideWindowKey);

    expect(entries.map(([id]) => id)).not.toContain(targetedKey);
    expect(entries.map(([id]) => id)).not.toContain(insideWindowBeforeKey);
    expect(entries.map(([id]) => id)).not.toContain(insideWindowAfterKey);
  });
});
