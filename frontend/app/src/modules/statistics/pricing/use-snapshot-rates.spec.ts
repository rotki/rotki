import type { MaybeRefOrGetter } from 'vue';
import type { BackfillDemand } from '@/modules/statistics/pricing/use-price-backfill';
import { BigNumber, PriceQuality, type ResolvedPrice } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { SNAPSHOT_RATES_DEMAND, useSnapshotRates } from '@/modules/statistics/pricing/use-snapshot-rates';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

const { register, requested, series } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return {
    register: vi.fn<(id: string, demand: MaybeRefOrGetter<BackfillDemand | undefined>) => void>(),
    requested: shallowRef<{ assets: readonly string[]; times: readonly number[] }>({ assets: [], times: [] }),
    series: shallowRef<ReadonlyMap<string, readonly ResolvedPrice[]>>(new Map()),
  };
});

vi.mock('@/modules/statistics/pricing/use-price-backfill', () => ({
  usePriceBackfill: (): { register: typeof register } => ({ register }),
}));

vi.mock('@/modules/statistics/pricing/use-price-series', () => ({
  usePriceSeries: (assets: MaybeRefOrGetter<readonly string[]>, times: MaybeRefOrGetter<readonly number[]>): { series: typeof series } => {
    watchImmediate([(): readonly string[] => toValue(assets), (): readonly number[] => toValue(times)], ([nextAssets, nextTimes]): void => set(requested, { assets: nextAssets, times: nextTimes }));
    return { series };
  },
}));

const times = [1000, 2000, 3000];

function setMainCurrency(symbol: string): void {
  const { findCurrency } = useCurrencies();
  useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(findCurrency(symbol)), mainCurrency: findCurrency(symbol) });
}

function registeredDemand(): BackfillDemand | undefined {
  const call = register.mock.calls.find(([id]) => id === SNAPSHOT_RATES_DEMAND);
  return call ? toValue(call[1]) : undefined;
}

describe('modules/statistics/pricing/use-snapshot-rates', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    register.mockClear();
    set(series, new Map());
    useStatisticsStore().netValue = { data: [new BigNumber('10'), new BigNumber('50'), new BigNumber('20')], times };
  });

  it('should ask for nothing while the main currency is USD', () => {
    withSetup(() => useSnapshotRates());
    expect(get(requested).assets).toEqual([]);
    expect(registeredDemand()).toBeUndefined();
  });

  it('should ask for the USD rate at every snapshot and fill it in the background', () => {
    setMainCurrency('EUR');
    withSetup(() => useSnapshotRates());

    expect(get(requested)).toEqual({ assets: ['USD'], times });
    expect(registeredDemand()).toEqual({ asset: 'USD', times });
  });

  it('should hand the resolved rates to the statistics store by snapshot time', async () => {
    setMainCurrency('EUR');
    withSetup(() => useSnapshotRates());
    const rate = { price: new BigNumber('0.9'), quality: PriceQuality.EXACT };
    set(series, new Map([['USD', [rate, rate, rate]]]));
    await nextTick();

    const result = useStatisticsStore().getNetValue(0);
    expect(result.data.slice(0, 3).map(value => value.toFixed())).toEqual(['9', '45', '18']);
  });
});
