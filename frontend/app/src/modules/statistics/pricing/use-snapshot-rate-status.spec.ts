import { BigNumber, type FailedHistoricalAssetPriceResponse, PriceQuality } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { DAY_SECONDS } from '@/modules/statistics/pricing/price-series';
import { useSnapshotRateStatus } from '@/modules/statistics/pricing/use-snapshot-rate-status';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

const { failedDailyPrices, rateLimited, resolvedFailedDailyPrices } = await vi.hoisted(async () => {
  const { ref: createRef, shallowRef: createShallowRef } = await import('vue');
  return {
    failedDailyPrices: createShallowRef<Record<string, FailedHistoricalAssetPriceResponse>>({}),
    rateLimited: createRef<boolean>(false),
    resolvedFailedDailyPrices: createShallowRef<Record<string, number[]>>({}),
  };
});

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): Record<string, unknown> => ({ failedDailyPrices, resolvedFailedDailyPrices }),
}));

vi.mock('@/modules/statistics/pricing/use-price-backfill', () => ({
  usePriceBackfill: (): Record<string, unknown> => ({ rateLimited }),
}));

const times = [10, 20, 30].map(day => day * DAY_SECONDS + 3600);

function setMainCurrency(symbol: string): void {
  const { findCurrency } = useCurrencies();
  useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(findCurrency(symbol)), mainCurrency: findCurrency(symbol) });
}

describe('modules/statistics/pricing/use-snapshot-rate-status', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(failedDailyPrices, {});
    set(resolvedFailedDailyPrices, {});
    set(rateLimited, false);
    const store = useStatisticsStore();
    store.netValue = { data: times.map(() => new BigNumber(1)), times };
    store.setSnapshotRates(new Map([
      [times[0], { price: new BigNumber('0.9'), quality: PriceQuality.EXACT, time: times[0] }],
      [times[1], { price: new BigNumber('0.9'), quality: PriceQuality.CARRIED, time: times[0] }],
    ]));
  });

  it('should report nothing in USD, where nothing is converted', () => {
    const { result } = withSetup(() => useSnapshotRateStatus());
    expect(get(result.status)).toEqual({ pending: 0, rateLimited: false, unavailable: 0 });
  });

  it('should count snapshots at a stand-in rate as pending until their day is known to have none', () => {
    setMainCurrency('EUR');
    const { result } = withSetup(() => useSnapshotRateStatus());
    expect(get(result.status)).toMatchObject({ pending: 2, unavailable: 0 });

    set(failedDailyPrices, { USD: { noPricesTimestamps: [20 * DAY_SECONDS], rateLimitedPricesTimestamps: [] } });
    expect(get(result.status)).toMatchObject({ pending: 1, unavailable: 1 });
  });

  it('should count a day as pending again once a rate was added for it by hand', () => {
    setMainCurrency('EUR');
    set(failedDailyPrices, { USD: { noPricesTimestamps: [20 * DAY_SECONDS], rateLimitedPricesTimestamps: [] } });
    set(resolvedFailedDailyPrices, { USD: [20 * DAY_SECONDS] });
    const { result } = withSetup(() => useSnapshotRateStatus());
    expect(get(result.status)).toMatchObject({ pending: 2, unavailable: 0 });
  });

  it('should pass the rate limit through', () => {
    setMainCurrency('EUR');
    set(rateLimited, true);
    const { result } = withSetup(() => useSnapshotRateStatus());
    expect(get(result.status).rateLimited).toBe(true);
  });
});
