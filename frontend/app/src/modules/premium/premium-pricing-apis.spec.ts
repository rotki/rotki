import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { BackfillDemand } from '@/modules/statistics/pricing/use-price-backfill';
import { BigNumber, PriceQuality, type ResolvedPrice } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usdRatesAt } from '@/modules/premium/premium-pricing-apis';

interface SeriesCall {
  assets: readonly string[];
  times: readonly number[];
}

const { register, seriesCalls } = vi.hoisted(() => {
  const calls: SeriesCall[] = [];
  return {
    register: vi.fn<(id: string, demand: MaybeRefOrGetter<BackfillDemand | undefined>) => void>(),
    seriesCalls: calls,
  };
});

vi.mock('@/modules/statistics/pricing/use-price-series', async () => {
  const { computed: createComputed } = await import('vue');
  const { BigNumber: Big, PriceQuality: Quality } = await import('@rotki/common');
  return {
    usePriceSeries: (assets: MaybeRefOrGetter<readonly string[]>, times: MaybeRefOrGetter<readonly number[]>): { series: ComputedRef<ReadonlyMap<string, readonly ResolvedPrice[]>> } => {
      seriesCalls.push({ assets: toValue(assets), times: toValue(times) });
      return {
        series: createComputed(() => new Map(toValue(assets).map((asset): [string, ResolvedPrice[]] =>
          [asset, toValue(times).map(() => ({ price: new Big('0.9'), quality: Quality.CARRIED }))]))),
      };
    },
  };
});

vi.mock('@/modules/statistics/pricing/use-price-backfill', () => ({
  usePriceBackfill: (): { register: typeof register } => ({ register }),
}));

describe('modules/premium/premium-pricing-apis', () => {
  beforeEach(() => {
    seriesCalls.length = 0;
    register.mockClear();
  });

  it('should give the USD rate at every requested time through one series', () => {
    const { result } = withSetup(() => usdRatesAt([5000, 6000]));
    expect(seriesCalls).toEqual([{ assets: ['USD'], times: [5000, 6000] }]);
    expect(get(result)).toEqual([
      { price: new BigNumber('0.9'), quality: PriceQuality.CARRIED },
      { price: new BigNumber('0.9'), quality: PriceQuality.CARRIED },
    ]);
  });

  it('should ask the background backfill for those times as one demand per call', () => {
    withSetup(() => [usdRatesAt([5000, 6000]), usdRatesAt([7000])]);
    const [[firstId, firstDemand], [secondId]] = register.mock.calls;
    expect(firstId).not.toBe(secondId);
    expect(toValue(firstDemand)).toEqual({ asset: 'USD', times: [5000, 6000] });
  });
});
