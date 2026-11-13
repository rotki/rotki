import type { ComputedRef } from 'vue';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useSetting } from '@/modules/settings/use-setting';
import { DAY_SECONDS, isFallbackQuality, nearestWithin } from '@/modules/statistics/pricing/price-series';
import { usePriceBackfill } from '@/modules/statistics/pricing/use-price-backfill';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

export interface SnapshotRateStatus {
  /** Snapshots still at a stand-in rate whose own rate is being fetched or waits its turn. */
  readonly pending: number;
  /** Snapshots still at a stand-in rate because the oracles have no rate for their day. */
  readonly unavailable: number;
  /** The last rate request hit a rate limit, so fetching waits longer before trying again. */
  readonly rateLimited: boolean;
}

interface UseSnapshotRateStatusReturn {
  readonly status: ComputedRef<SnapshotRateStatus>;
}

/**
 * Where the USD rates of the net value snapshots stand, for the chart to explain its estimates.
 *
 * @remarks
 * A snapshot converted at a stand-in rate is unavailable when the backend has reported no rate for
 * its day (and none was added by hand since), and pending otherwise. In USD nothing is converted,
 * so nothing is reported.
 */
export function useSnapshotRateStatus(): UseSnapshotRateStatusReturn {
  const { netValue, snapshotRates } = storeToRefs(useStatisticsStore());
  const { failedDailyPrices, resolvedFailedDailyPrices } = useHistoricPriceCache();
  const { rateLimited } = usePriceBackfill();
  const currencySymbol = useSetting('currencySymbol');

  /** Days the backend has no USD rate for, leaving out those a rate was added for by hand, in order. */
  const noRateDays = computed<{ time: number }[]>(() => {
    const resolved = new Set(get(resolvedFailedDailyPrices)[CURRENCY_USD] ?? []);
    return (get(failedDailyPrices)[CURRENCY_USD]?.noPricesTimestamps ?? [])
      .filter(day => !resolved.has(day))
      .sort((a, b) => a - b)
      .map(time => ({ time }));
  });

  const status = computed<SnapshotRateStatus>(() => {
    let pending = 0;
    let unavailable = 0;
    if (get(currencySymbol) !== CURRENCY_USD) {
      const rates = get(snapshotRates);
      for (const time of get(netValue).times) {
        const rate = rates.get(time);
        if (rate && !isFallbackQuality(rate.quality))
          continue;
        if (nearestWithin(get(noRateDays), time, DAY_SECONDS))
          unavailable += 1;
        else
          pending += 1;
      }
    }
    return { pending, rateLimited: get(rateLimited), unavailable };
  });

  return { status };
}
