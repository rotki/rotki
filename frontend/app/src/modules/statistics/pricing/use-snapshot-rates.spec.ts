import type { MaybeRefOrGetter } from 'vue';
import { BigNumber, PriceQuality, type ResolvedPrice } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SNAPSHOT_RATES_DEMAND, useSnapshotRates } from '@/modules/statistics/pricing/use-snapshot-rates';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

const { rates, requested } = await vi.hoisted(async () => {
  const { shallowRef } = await import('vue');
  return {
    rates: shallowRef<readonly ResolvedPrice[]>([]),
    requested: shallowRef<{ id: string; times: readonly number[] }>({ id: '', times: [] }),
  };
});

vi.mock('@/modules/statistics/pricing/use-usd-rates', () => ({
  useUsdRates: (id: string, times: MaybeRefOrGetter<readonly number[]>): { rates: typeof rates } => {
    watchImmediate((): readonly number[] => toValue(times), (nextTimes): void => set(requested, { id, times: nextTimes }));
    return { rates };
  },
}));

const times = [1000, 2000, 3000];

describe('modules/statistics/pricing/use-snapshot-rates', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    set(rates, []);
    useStatisticsStore().netValue = { data: [new BigNumber('10'), new BigNumber('50'), new BigNumber('20')], times };
  });

  it('should ask for the USD rate at every snapshot under its own demand', () => {
    withSetup(() => useSnapshotRates());
    expect(get(requested)).toEqual({ id: SNAPSHOT_RATES_DEMAND, times });
  });

  it('should hand the resolved rates to the statistics store by snapshot time', async () => {
    withSetup(() => useSnapshotRates());
    const rate = { price: new BigNumber('0.9'), quality: PriceQuality.EXACT };
    set(rates, [rate, rate, rate]);
    await nextTick();

    expect([...useStatisticsStore().snapshotRates.keys()]).toEqual(times);
  });

  it('should leave the store alone when the rates did not change', async () => {
    withSetup(() => useSnapshotRates());
    const store = useStatisticsStore();
    set(rates, times.map(() => ({ price: new BigNumber('0.9'), quality: PriceQuality.EXACT })));
    await nextTick();
    const written = store.snapshotRates;

    set(rates, times.map(() => ({ price: new BigNumber('0.9'), quality: PriceQuality.EXACT })));
    await nextTick();

    expect(store.snapshotRates).toBe(written);
  });
});
