import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef } from 'vue';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useSetting } from '@/modules/settings/use-setting';
import { dayStart } from '@/modules/statistics/pricing/backfill-plan';
import { isFallbackQuality } from '@/modules/statistics/pricing/price-series';
import { usePriceBackfill } from '@/modules/statistics/pricing/use-price-backfill';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

export interface SnapshotRateStatus {
  /** Snapshots still at a stand-in rate whose own rate is being fetched or waits its turn. */
  readonly pending: number;
  /**
   * Snapshots still at a stand-in rate because the oracles have no rate for their day, or could not
   * be reached for it for so long that the backfill stopped asking.
   */
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
 * its day or the backfill gave up on it as unreachable (and no rate was added by hand since), and
 * pending otherwise. In USD nothing is converted,
 * so nothing is reported.
 */
export function useSnapshotRateStatus(): UseSnapshotRateStatusReturn {
  const { netValue, snapshotRates } = storeToRefs(useStatisticsStore());
  const { failedDailyPrices, resolvedFailedDailyPrices } = useHistoricPriceCache();
  const { givenUpDays, rateLimited } = usePriceBackfill();
  const currencySymbol = useSetting('currencySymbol');

  /**
   * Days nothing will fetch a USD rate for: the backend has none, or the backfill gave up on them
   * and they are still filed as not fetched (a later fetch may have priced them). Leaves out those
   * a rate was added for by hand.
   */
  const noRateDays = computed<ReadonlySet<number>>(() => {
    const filed = get(failedDailyPrices)[CURRENCY_USD];
    const notFetched = new Set((filed?.failedPricesTimestamps ?? []).map(dayStart));
    const days = new Set([
      ...(filed?.noPricesTimestamps ?? []).map(dayStart),
      ...Array.from(givenUpDays(CURRENCY_USD), dayStart).filter(day => notFetched.has(day)),
    ]);
    for (const day of get(resolvedFailedDailyPrices)[CURRENCY_USD] ?? [])
      days.delete(dayStart(day));
    return days;
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
        if (get(noRateDays).has(dayStart(time)))
          unavailable += 1;
        else
          pending += 1;
      }
    }
    return { pending, rateLimited: get(rateLimited), unavailable };
  });

  return { status };
}
