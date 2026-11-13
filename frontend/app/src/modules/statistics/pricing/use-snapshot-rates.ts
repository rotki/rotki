import { type BigNumber, type ResolvedPrice, Zero } from '@rotki/common';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
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
  const { series } = usePriceSeries(assets, times);

  const demand = computed<BackfillDemand | undefined>(() => {
    const { data, times: snapshotTimes } = get(netValue);
    if (get(assets).length === 0 || snapshotTimes.length < 2)
      return undefined;
    const largest = data.reduce<BigNumber>((max, value) => (value.gt(max) ? value : max), Zero);
    return {
      holdings: [{ asset: CURRENCY_USD, heldValue: largest }],
      range: { end: Math.max(...snapshotTimes), start: Math.min(...snapshotTimes) },
    };
  });

  usePriceBackfill().register(SNAPSHOT_RATES_DEMAND, demand);

  watchImmediate(series, (resolved) => {
    const rates = resolved.get(CURRENCY_USD) ?? [];
    const entries = get(times).flatMap((time, index): [number, ResolvedPrice][] => {
      const rate = rates[index];
      return rate ? [[time, rate]] : [];
    });
    store.setSnapshotRates(new Map(entries));
  });
}
