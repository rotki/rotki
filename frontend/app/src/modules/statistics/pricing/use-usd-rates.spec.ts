import type { MaybeRefOrGetter } from 'vue';
import type { BackfillDemand } from '@/modules/statistics/pricing/use-price-backfill';
import { BigNumber, PriceQuality } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';
import { useUsdRates } from '@/modules/statistics/pricing/use-usd-rates';

const { readCached, register, resolvedFailedDailyPrices } = await vi.hoisted(async () => {
  const { shallowRef: createShallowRef } = await import('vue');
  return {
    readCached: vi.fn<(asset: string, times: readonly number[], force?: boolean) => Promise<void>>(async () => {}),
    register: vi.fn<(id: string, demand: MaybeRefOrGetter<BackfillDemand | undefined>) => void>(),
    resolvedFailedDailyPrices: createShallowRef<Record<string, number[]>>({}),
  };
});

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): { resolvedFailedDailyPrices: typeof resolvedFailedDailyPrices } => ({ resolvedFailedDailyPrices }),
}));

vi.mock('@/modules/statistics/pricing/use-price-cache-reader', () => ({
  usePriceCacheReader: (): { readCached: typeof readCached } => ({ readCached }),
}));

vi.mock('@/modules/statistics/pricing/use-price-backfill', () => ({
  usePriceBackfill: (): { register: typeof register } => ({ register }),
}));

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): { getExchangeRate: (currency: string) => BigNumber | undefined } => ({
    getExchangeRate: (): BigNumber => new BigNumber('0.9'),
  }),
}));

function setMainCurrency(symbol: string): void {
  const { findCurrency } = useCurrencies();
  useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(findCurrency(symbol)), mainCurrency: findCurrency(symbol) });
}

function registeredDemand(): BackfillDemand | undefined {
  const call = register.mock.calls.at(-1);
  return call ? toValue(call[1]) : undefined;
}

describe('modules/statistics/pricing/use-usd-rates', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    readCached.mockClear();
    register.mockClear();
    set(resolvedFailedDailyPrices, {});
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should give one for every time in USD, reading and fetching nothing', async () => {
    const { result } = withSetup(() => useUsdRates('rates', [SECONDS_PER_DAY, 2 * SECONDS_PER_DAY]));
    await vi.advanceTimersByTimeAsync(400);

    expect(get(result.rates).map(item => [item.quality, item.price?.toFixed()]))
      .toEqual([[PriceQuality.EXACT, '1'], [PriceQuality.EXACT, '1']]);
    expect(readCached).not.toHaveBeenCalled();
    expect(registeredDemand()).toBeUndefined();
  });

  it('should resolve from the cached rates, falling back to today\'s rate', () => {
    setMainCurrency('EUR');
    usePriceSeriesStore().addPrices('USD', [{ price: new BigNumber('0.8'), time: SECONDS_PER_DAY }]);
    const { result } = withSetup(() => useUsdRates('rates', [SECONDS_PER_DAY]));

    expect(get(result.rates)).toEqual([{ price: new BigNumber('0.8'), quality: PriceQuality.EXACT, time: SECONDS_PER_DAY }]);
  });

  it('should use today\'s rate while nothing is cached', () => {
    setMainCurrency('EUR');
    const { result } = withSetup(() => useUsdRates('rates', [SECONDS_PER_DAY]));
    expect(get(result.rates)).toEqual([{ price: new BigNumber('0.9'), quality: PriceQuality.CURRENT }]);
  });

  it('should read the cache once the times settle and ask the backfill for them', async () => {
    setMainCurrency('EUR');
    const times = ref<number[]>([SECONDS_PER_DAY]);
    withSetup(() => useUsdRates('rates', times));
    await vi.advanceTimersByTimeAsync(400);
    set(times, [SECONDS_PER_DAY, 2 * SECONDS_PER_DAY]);
    await vi.advanceTimersByTimeAsync(400);

    expect(readCached).toHaveBeenLastCalledWith('USD', [SECONDS_PER_DAY, 2 * SECONDS_PER_DAY]);
    expect(register).toHaveBeenCalledWith('rates', expect.anything());
    expect(registeredDemand()).toEqual({ asset: 'USD', times: [SECONDS_PER_DAY, 2 * SECONDS_PER_DAY] });
  });

  it('should drop every cached rate when the main currency changes', async () => {
    setMainCurrency('EUR');
    const store = usePriceSeriesStore();
    store.addPrices('USD', [{ price: new BigNumber('0.8'), time: SECONDS_PER_DAY }]);
    store.markRequested(['USD:86400']);

    setMainCurrency('GBP');
    await nextTick();

    expect(store.prices).toEqual({});
    expect(store.isRequested('USD:86400')).toBe(false);
  });

  it('should read the cache again in a new non-USD currency', async () => {
    setMainCurrency('EUR');
    withSetup(() => useUsdRates('rates', [SECONDS_PER_DAY]));
    await vi.advanceTimersByTimeAsync(400);
    readCached.mockClear();

    setMainCurrency('GBP');
    await vi.advanceTimersByTimeAsync(400);

    expect(readCached).toHaveBeenCalledWith('USD', [SECONDS_PER_DAY]);
  });

  it('should read the cache again after a rate is added by hand', async () => {
    setMainCurrency('EUR');
    withSetup(() => useUsdRates('rates', [SECONDS_PER_DAY]));
    await vi.advanceTimersByTimeAsync(400);
    readCached.mockClear();

    set(resolvedFailedDailyPrices, { USD: [SECONDS_PER_DAY] });
    await nextTick();

    expect(readCached).toHaveBeenCalledWith('USD', [SECONDS_PER_DAY], true);
  });
});
