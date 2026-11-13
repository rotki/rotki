import type { FailedHistoricalAssetPriceResponse, HistoricalAssetPricePayload } from '@rotki/common';
import type { ComputedRef } from 'vue';
import { createCustomPinia } from '@test/utils/create-pinia';
import { withSetup } from '@test/utils/with-setup';
import { setActivePinia } from 'pinia';
import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { BACKOFF_START_MS, REQUEST_DELAY_MS } from '@/modules/statistics/pricing/backfill-pacing';
import { type BackfillDemand, usePriceBackfill } from '@/modules/statistics/pricing/use-price-backfill';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

/** The response as the backend sends it, before parsing, or `fail` for a request that fails outright. */
type RawPriceResponse = {
  noPricesTimestamps: number[];
  prices: Record<string, string>;
  rateLimitedPricesTimestamps: number[];
} | 'fail' | 'malformed' | 'cancel';

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

vi.mock('@/modules/task-center/use-native-task', async (): Promise<unknown> => {
  const { Cancelled, TaskFailed } = await import('@/modules/core/tasks/task-result');
  return {
    useNativeTask: (): { cancelByPrefix: typeof cancelByPrefix; submitTask: (spec: { run: (ctx: unknown) => Promise<unknown> }) => Promise<unknown> } => ({
      cancelByPrefix,
      submitTask: async (spec: { run: (ctx: unknown) => Promise<unknown> }): Promise<unknown> => spec.run({
        cancelled: (): boolean => false,
        report: vi.fn(),
        rerun: false,
        runTask: async (task: () => Promise<unknown>): Promise<unknown> => {
          await task();
          const next = responses.shift() ?? { noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: [] };
          if (next === 'malformed')
            return ok({ prices: 'not a price map' });
          if (next === 'cancel')
            return err(Cancelled({ message: 'cancelled from the task center' }));
          return next === 'fail' ? err(TaskFailed({ message: 'the backend rejected the request' })) : ok(next);
        },
      }),
    }),
  };
});

const days = [0, 1, 2, 3].map(day => day * SECONDS_PER_DAY);

function flatPrices(times: number[], price = '10'): Record<string, string> {
  return Object.fromEntries(times.map(time => [time.toString(), price]));
}

function demand(): BackfillDemand {
  return { asset: 'BTC', times: days.map(day => day + SECONDS_PER_DAY / 2) };
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

  it('should start with a coarse rate, store the prices and stop once settled', async () => {
    responses.push({ noPricesTimestamps: [], prices: flatPrices(days), rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 5);

    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
    expect(queryHistoricalAssetPrices).toHaveBeenCalledWith(expect.objectContaining({
      asset: 'BTC',
      excludeTimestamps: [SECONDS_PER_DAY],
      fromTimestamp: 0,
      interval: SECONDS_PER_DAY,
      toTimestamp: SECONDS_PER_DAY,
    }));
    expect(usePriceSeriesStore().prices.BTC).toHaveLength(days.length);
  });

  it('should remember days with no price and not ask for them again', async () => {
    const failed = days[2];
    responses.push({ noPricesTimestamps: [failed], prices: flatPrices(days.filter(day => day !== failed)), rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 5);

    expect(get(failedDailyPrices).BTC?.noPricesTimestamps).toEqual([failed]);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
  });

  it('should back off after a rate limit before asking again, and say so', async () => {
    responses.push({ noPricesTimestamps: [], prices: {}, rateLimitedPricesTimestamps: days });
    const { result } = withSetup(() => {
      const backfill = usePriceBackfill();
      backfill.register('rates', demand());
      return backfill;
    });
    await vi.advanceTimersByTimeAsync(BACKOFF_START_MS - 1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
    expect(get(result.rateLimited)).toBe(true);

    await vi.advanceTimersByTimeAsync(1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
  });

  it('should back off after a failed request and move on, without calling its days priceless', async () => {
    responses.push('fail');
    const { result } = withSetup(() => {
      const backfill = usePriceBackfill();
      backfill.register('rates', demand());
      return backfill;
    });
    await vi.advanceTimersByTimeAsync(BACKOFF_START_MS - 1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(1);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
    expect(queryHistoricalAssetPrices).toHaveBeenLastCalledWith(expect.objectContaining({ fromTimestamp: days[1], toTimestamp: days[3] }));
    expect(get(failedDailyPrices).BTC).toBeUndefined();
    expect(get(result.rateLimited)).toBe(false);
  });

  it('should move on past a malformed response rather than blame the oracles or stall', async () => {
    responses.push('malformed');
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 5);

    expect(get(failedDailyPrices).BTC).toBeUndefined();
    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
    expect(queryHistoricalAssetPrices).toHaveBeenLastCalledWith(expect.objectContaining({ fromTimestamp: days[1], toTimestamp: days[3] }));
  });

  it('should stop for the session once the user cancels one of its activities', async () => {
    responses.push('cancel');
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS * 5);

    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();
  });

  it('should start over in a new main currency instead of skipping days it tried in the old one', async () => {
    responses.push({ noPricesTimestamps: [], prices: flatPrices(days), rateLimitedPricesTimestamps: [] });
    withSetup(() => usePriceBackfill().register('rates', demand()));
    await vi.advanceTimersByTimeAsync(REQUEST_DELAY_MS);
    expect(queryHistoricalAssetPrices).toHaveBeenCalledOnce();

    const { findCurrency } = useCurrencies();
    useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(findCurrency('EUR')), mainCurrency: findCurrency('EUR') });
    await vi.advanceTimersByTimeAsync(0);

    expect(queryHistoricalAssetPrices).toHaveBeenCalledTimes(2);
    expect(cancelByPrefix).toHaveBeenCalledWith('prices', 'backfill');
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
});
