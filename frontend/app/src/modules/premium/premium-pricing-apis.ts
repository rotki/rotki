import type { ResolvedPrice, StatisticsApi } from '@rotki/common';
import type { ComputedRef } from 'vue';
import { useUsdRates } from '@/modules/statistics/pricing/use-usd-rates';

let rateDemands = 0;

/**
 * The USD to main currency rates at a set of times, for the premium graphs that convert stored USD
 * values.
 *
 * @remarks
 * Goes through the same rates and background backfill as the dashboard net value, so a rate
 * missing from the cache is flagged until it is fetched, and fetching it sharpens both. Each call is
 * one backfill demand, whatever the number of times.
 */
export const usdRatesAt: StatisticsApi['usdRatesAt'] = (times): ComputedRef<readonly ResolvedPrice[]> =>
  useUsdRates(`premium-usd-rates-${++rateDemands}`, times).rates;
