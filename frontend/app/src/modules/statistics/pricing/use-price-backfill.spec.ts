import type { ComputedRef } from 'vue';
import { bigNumberify, type FailedHistoricalAssetPriceResponse, type HistoricalAssetPricePayload } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { withSetup } from '@test/utils/with-setup';
import { setActivePinia } from 'pinia';
import { ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BACKOFF_START_MS, REQUEST_DELAY_MS } from '@/modules/statistics/pricing/backfill-pacing';
import { ANCHOR_COUNT } from '@/modules/statistics/pricing/backfill-plan';
import { DAY_SECONDS } from '@/modules/statistics/pricing/price-series';
import { type BackfillDemand, usePriceBackfill } from '@/modules/statistics/pricing/use-price-backfill';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

/** The response as the backend sends it, before parsing. */
interface RawPriceResponse {
  noPricesTimestamps: number[];
  prices: Record<string, string>;
  rateLimitedPricesTimestamps: number[];
}

const { cancelByPrefix, failedDailyPrices, focused, queryHistoricalAssetPrices, responses } = await vi.hoisted(async () => {
  const { ref, shallowRef } = await import('vue');
  const pending: RawPriceResponse[] = [];
  return {
    cancelByPrefix: vi.fn(),
    failedDailyPrices: shallowRef<Record<string, FailedHistoricalAssetPriceResponse>>({}),
    focused: ref<boolean>(true),
    queryHistoricalAssetPrices: vi.fn<(payload: HistoricalAssetPricePayload) => Promise<{ taskId: number }>>(async () => ({ taskId: 1 })),
    responses: pending,
  };
});

vi.mock('@vueuse/core', async (importOriginal): Promise<typeof import('@vueuse/core')> => ({
  ...await importOriginal<typeof import('@vueuse/core')>(),
  useWindowFocus: (): typeof focused => focused,
}));

vi.mock('@/modules/statistics/api/use-statistics-api', () => ({
  useStatisticsApi: (): { queryHistoricalAssetPrices: typeof queryHistoricalAssetPrices } => ({ queryHistoricalAssetPrices }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): { failedDailyPrices: typeof failedDailyPrices } => ({ failedDailyPrices }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { getAssetField: (asset: string) => string } => ({ getAssetField: (asset: string): string => asset }),
}));

vi.mock('@/modules/task-center/use-task-center', async (): Promise<unknown> => {
  const { computed } = await import('vue');
  return {
    useTaskCenter: (): { useIsActivePrefix: () => ComputedRef<boolean> } => ({ useIsActivePrefix: (): ComputedRef<boolean> => computed<boolean>(() => false) }),
  };
});

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): { cancelByPrefix: typeof cancelByPrefix; submitTask: (spec: { run: (ctx: unknown) => Promise<unknown> }) => Promise<unknown> } => ({
    cancelByPrefix,
    submitTask: async (spec: { run: (ctx: unknown) => Promise<unknown> }): Promise<unknown> => spec.run({
      cancelled: (): boolean => false,
      report: vi.fn(),
      rerun: false,
      runTask: async (task: () => Promise<unknown>): Promise<unknown> => {
        await task();
        return ok(responses.shift() ?? { noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] });
      },
    }),
  }),
}));

const range = { end: 70 * DAY_SECONDS, start: 0 };
const anchorTimes = Array.from({ length: ANCHOR_COUNT }, (_, index) => index * 10 * DAY_SECONDS);

function flatPrices(times: number[], price = '10'): Record<string, string> {
  return Object.fromEntries(times.map(time => [time.toString(), price]));
}

function demand(): BackfillDemand {
  return { holdings: [{ asset: 'BTC', heldValue: bigNumberify(100) }], range };
}

describe('modules/statistics/pricing/use-price-backfill', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createCustomPinia());
    set(focused, true);
    set(failedDailyPrices, {});
    responses.length = 0;
    queryHistoricalAssetPrices.mockClear();
    cancelByPrefix.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should fetch nothing while nothing is registered', async () => {
    withSetup(() => usePriceBackfill());
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 3);
    expect(queryHistoricalAssetPrices).not.toHaveBeenCalled();
  });

  it('should fetch a demand\'s anchors in the background, store the prices and stop once refined', async () => {
    responses.push({ noPricesTimestamps: [], prices: flatPrices(anchorTimes), rateLimitedPricesTimestamps: [] });
    const { result } = withSetup(() => {
      const backfill = usePriceBackfill();
      backfill.register('rates', demand());
      return backfill;
    });
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS);

    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
    expect(queryHistoricalAssetPrices).toHaveBeenCalledWith(expect.objectContaining({ asset: 'BTC', fromTimestamp: 0, interval: 10 * DAY_SECONDS }));
    expect(usePriceSeriesStore().mainPrices.BTC).toHaveLength(ANCHOR_COUNT);
    expect(get(result.running)).toBe(false);
  });

  it('should remember times with no price and not ask for them again', async () => {
    const failed = anchorTimes[3];
    responses.push({
      noPricesTimestamps: [failed],
      prices: flatPrices(anchorTimes.filter(time => time !== failed)),
      rateLimitedPricesTimestamps: [],
    });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 20);

    expect(get(failedDailyPrices).BTC?.noPricesTimestamps).toEqual([failed]);
    const later = queryHistoricalAssetPrices.mock.calls.slice(1).map(([payload]) => payload);
    expect(later.length).toBeGreaterThan(0);
    for (const { excludeTimestamps = [], fromTimestamp, interval, toTimestamp } of later) {
      const asked = Array.from({ length: Math.floor((toTimestamp - fromTimestamp) / interval) + 1 }, (_, index) => fromTimestamp + index * interval)
        .filter(time => !excludeTimestamps.includes(time));
      expect(asked).not.toContain(failed);
    }
  });

  it('should back off after a rate limit before asking again', async () => {
    responses.push({ noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: anchorTimes });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(BACKOFF_START_MS - 1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
  });

  it('should pause while the window is unfocused and resume when it comes back', async () => {
    set(focused, false);
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS);
    expect(queryHistoricalAssetPrices).not.toHaveBeenCalled();

    set(focused, true);
    await vi.advanceTimersByTimeAsync(0);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
  });

  it('should cancel the in-flight request on stop', () => {
    const { result } = withSetup(() => usePriceBackfill());
    result.stop();
    expect(cancelByPrefix).toHaveBeenCalledWith('prices', 'backfill');
  });
});
