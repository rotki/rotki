import type { ResolvedPrice } from '@rotki/common';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useSetting } from '@/modules/settings/use-setting';
import { type BackfillDemand, usePriceBackfill } from '@/modules/statistics/pricing/use-price-backfill';
import { usePriceSeries } from '@/modules/statistics/pricing/use-price-series';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

/** The backfill demand id of the snapshot rates. */
export const SNAPSHOT_RATES_DEMAND = 'snapshot-usd-rates';

/**
 * Keeps the statistics store's USD to main currency rate for every net value snapshot current.
 *
 * @remarks
 * Snapshots are stored in USD, so each needs the rate of its own time (rotki/rotki#4031). The rates
 * are read from the price cache and the missing ones are filled in the background: a currency rate
 * tells the oracle the main currency and nothing about holdings.
 * Nothing is read or fetched when the main currency is USD.
 *
 * Call once, from an app-level scope.
 */
export function useSnapshotRates(): void {
  const store = useStatisticsStore();
  const { netValue } = storeToRefs(store);
  const currencySymbol = useSetting('currencySymbol');

  const times = computed<number[]>(() => get(netValue).times);
  const assets = computed<string[]>(() => (get(currencySymbol) === CURRENCY_USD || get(times).length === 0 ? [] : [CURRENCY_USD]));
  const { reload, series } = usePriceSeries(assets, times);
  const { resolvedFailedDailyPrices } = useHistoricPriceCache();

  const demand = computed<BackfillDemand | undefined>(() =>
    (get(assets).length === 0 ? undefined : { asset: CURRENCY_USD, times: get(times) }));

  usePriceBackfill().register(SNAPSHOT_RATES_DEMAND, demand);

  /** A rate entered by hand for a day the oracles had none is in the cache now, so read it. */
  watch(() => get(resolvedFailedDailyPrices)[CURRENCY_USD], async () => reload());

  watchImmediate(series, (resolved) => {
    const rates = resolved.get(CURRENCY_USD) ?? [];
    const entries = get(times).flatMap((time, index): [number, ResolvedPrice][] => {
      const rate = rates[index];
      return rate ? [[time, rate]] : [];
    });
    store.setSnapshotRates(new Map(entries));
  });
}
