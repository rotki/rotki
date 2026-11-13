import type { ComputedRef } from 'vue';
import { One, PriceQuality, type ResolvedPrice, type StatisticsApi } from '@rotki/common';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { type BackfillDemand, usePriceBackfill } from '@/modules/statistics/pricing/use-price-backfill';
import { usePriceSeries } from '@/modules/statistics/pricing/use-price-series';

const MISSING: ResolvedPrice = { price: undefined, quality: PriceQuality.MISSING };

let rateDemands = 0;

/**
 * The USD to main currency rate at one time, for the premium graphs that convert stored USD values.
 *
 * @remarks
 * Goes through the same price series and background backfill as the dashboard net value, so a rate
 * missing from the cache is flagged until it is fetched, and fetching it sharpens both.
 */
export const usdRateAt: StatisticsApi['usdRateAt'] = (timestamp): ComputedRef<ResolvedPrice> => {
  const { series } = usePriceSeries([CURRENCY_USD], () => [toValue(timestamp)]);
  const demand = computed<BackfillDemand>(() => {
    const time = toValue(timestamp);
    return { holdings: [{ asset: CURRENCY_USD, heldValue: One }], range: { end: time, start: time } };
  });
  usePriceBackfill().register(`premium-usd-rate-${++rateDemands}`, demand);
  return computed<ResolvedPrice>(() => get(series).get(CURRENCY_USD)?.[0] ?? MISSING);
};
