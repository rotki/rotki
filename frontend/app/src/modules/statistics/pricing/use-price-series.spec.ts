import { BigNumber, PriceQuality } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { DAY_SECONDS } from '@/modules/statistics/pricing/price-series';
import { usePriceSeries } from '@/modules/statistics/pricing/use-price-series';
import { PricePair, usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

const { readCached } = vi.hoisted(() => ({
  readCached: vi.fn<(assets: readonly string[], times: readonly number[]) => Promise<void>>(async () => {}),
}));

vi.mock('@/modules/statistics/pricing/use-price-cache-reader', () => ({
  usePriceCacheReader: (): { readCached: typeof readCached } => ({ readCached }),
}));

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): { getAssetPrice: (asset: string) => BigNumber | undefined; getExchangeRate: (currency: string) => BigNumber | undefined } => ({
    getAssetPrice: (asset: string): BigNumber | undefined => (asset === 'BTC' ? new BigNumber('50000') : undefined),
    getExchangeRate: (): BigNumber => new BigNumber('0.9'),
  }),
}));

function setMainCurrency(symbol: string): void {
  const { findCurrency } = useCurrencies();
  useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(findCurrency(symbol)), mainCurrency: findCurrency(symbol) });
}

describe('modules/statistics/pricing/use-price-series', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    readCached.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should resolve each asset from the cached prices, falling back to today\'s price', () => {
    usePriceSeriesStore().addPrices(PricePair.MAIN, 'ETH', [{ price: new BigNumber('3000'), time: DAY_SECONDS }]);
    const { result } = withSetup(() => usePriceSeries(['ETH', 'BTC', 'SPAM'], [DAY_SECONDS]));

    const series = get(result.series);
    expect(series.get('ETH')).toEqual([{ price: new BigNumber('3000'), quality: PriceQuality.EXACT }]);
    expect(series.get('BTC')).toEqual([{ price: new BigNumber('50000'), quality: PriceQuality.CURRENT }]);
    expect(series.get('SPAM')).toEqual([{ price: undefined, quality: PriceQuality.MISSING }]);
  });

  it('should price the main currency itself at one without reading anything', () => {
    setMainCurrency('EUR');
    const { result } = withSetup(() => usePriceSeries(['EUR'], [DAY_SECONDS, 2 * DAY_SECONDS]));
    expect(get(result.series).get('EUR')?.map(item => [item.quality, item.price?.toFixed()]))
      .toEqual([[PriceQuality.EXACT, '1'], [PriceQuality.EXACT, '1']]);
  });

  it('should price through USD after a currency switch left only USD prices cached', () => {
    setMainCurrency('EUR');
    const store = usePriceSeriesStore();
    store.addPrices(PricePair.USD, 'ETH', [{ price: new BigNumber('3000'), time: DAY_SECONDS }]);
    store.addPrices(PricePair.MAIN, 'USD', [{ price: new BigNumber('0.9'), time: DAY_SECONDS }]);

    const { result } = withSetup(() => usePriceSeries(['ETH'], [DAY_SECONDS]));

    expect(get(result.series).get('ETH')?.map(item => [item.quality, item.price?.toFixed()])).toEqual([[PriceQuality.DERIVED, '2700']]);
  });

  it('should read the cache once the requested assets and times settle', async () => {
    const times = ref<number[]>([DAY_SECONDS]);
    withSetup(() => usePriceSeries(['ETH'], times));
    await vi.advanceTimersByTimeAsync(400);
    set(times, [DAY_SECONDS, 2 * DAY_SECONDS]);
    await vi.advanceTimersByTimeAsync(400);

    expect(readCached).toHaveBeenLastCalledWith(['ETH'], [DAY_SECONDS, 2 * DAY_SECONDS]);
  });

  it('should drop every cached price when the main currency changes', async () => {
    const store = usePriceSeriesStore();
    store.addPrices(PricePair.MAIN, 'ETH', [{ price: new BigNumber('3000'), time: DAY_SECONDS }]);
    store.markRequested(['main:ETH:86400']);

    setMainCurrency('EUR');
    await nextTick();

    expect(store.mainPrices).toEqual({});
    expect(store.requested.size).toBe(0);
  });
});
