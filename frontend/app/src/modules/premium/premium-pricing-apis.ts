import type { ResolvedPrice, StatisticsApi } from '@rotki/common';
import type { ComputedRef } from 'vue';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { type BackfillDemand, usePriceBackfill } from '@/modules/statistics/pricing/use-price-backfill';
import { usePriceSeries } from '@/modules/statistics/pricing/use-price-series';

let rateDemands = 0;

/**
 * The USD to main currency rates at a set of times, for the premium graphs that convert stored USD
 * values.
 *
 * @remarks
 * Goes through the same price series and background backfill as the dashboard net value, so a rate
 * missing from the cache is flagged until it is fetched, and fetching it sharpens both. Each call is
 * one series and one backfill demand, whatever the number of times.
 */
export const usdRatesAt: StatisticsApi['usdRatesAt'] = (times): ComputedRef<readonly ResolvedPrice[]> => {
  const { series } = usePriceSeries([CURRENCY_USD], times);
  const demand = computed<BackfillDemand>(() => ({ asset: CURRENCY_USD, times: toValue(times) }));
  usePriceBackfill().register(`premium-usd-rates-${++rateDemands}`, demand);
  return computed<readonly ResolvedPrice[]>(() => get(series).get(CURRENCY_USD) ?? []);
};
