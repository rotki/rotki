import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { BigNumber, PriceQuality, type ResolvedPrice } from '@rotki/common';
import { withSetup } from '@test/utils/with-setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usdRatesAt } from '@/modules/premium/premium-pricing-apis';

interface RatesCall {
  id: string;
  times: readonly number[];
}

const { ratesCalls } = vi.hoisted(() => {
  const calls: RatesCall[] = [];
  return { ratesCalls: calls };
});

vi.mock('@/modules/statistics/pricing/use-usd-rates', async () => {
  const { computed: createComputed } = await import('vue');
  const { BigNumber: Big, PriceQuality: Quality } = await import('@rotki/common');
  return {
    useUsdRates: (id: string, times: MaybeRefOrGetter<readonly number[]>): { rates: ComputedRef<readonly ResolvedPrice[]> } => {
      ratesCalls.push({ id, times: toValue(times) });
      return { rates: createComputed(() => toValue(times).map(() => ({ price: new Big('0.9'), quality: Quality.CARRIED }))) };
    },
  };
});

describe('modules/premium/premium-pricing-apis', () => {
  beforeEach(() => {
    ratesCalls.length = 0;
  });

  it('should give the USD rate at every requested time', () => {
    const { result } = withSetup(() => usdRatesAt([5000, 6000]));
    expect(get(result)).toEqual([
      { price: new BigNumber('0.9'), quality: PriceQuality.CARRIED },
      { price: new BigNumber('0.9'), quality: PriceQuality.CARRIED },
    ]);
  });

  it('should register one backfill demand per call', () => {
    withSetup(() => [usdRatesAt([5000, 6000]), usdRatesAt([7000])]);
    const [first, second] = ratesCalls;
    expect(first.id).not.toBe(second.id);
    expect(first.times).toEqual([5000, 6000]);
  });
});
