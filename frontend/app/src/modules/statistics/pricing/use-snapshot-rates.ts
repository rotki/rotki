import type { ResolvedPrice } from '@rotki/common';
import { useUsdRates } from '@/modules/statistics/pricing/use-usd-rates';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

/** The backfill demand id of the snapshot rates. */
export const SNAPSHOT_RATES_DEMAND = 'snapshot-usd-rates';

function sameRate(a: ResolvedPrice | undefined, b: ResolvedPrice): boolean {
  return !!a && a.quality === b.quality && a.time === b.time
    && (a.price === b.price || (!!a.price && !!b.price && a.price.eq(b.price)));
}

/**
 * Keeps the statistics store's USD to main currency rate for every net value snapshot current.
 *
 * @remarks
 * Snapshots are stored in USD, so each needs the rate of its own time (rotki/rotki#4031). The store
 * is only written when a rate changed, so the chart does not redraw on every cache read.
 *
 * Call once, from an app-level scope.
 */
export function useSnapshotRates(): void {
  const store = useStatisticsStore();
  const { netValue, snapshotRates } = storeToRefs(store);

  const times = computed<number[]>(() => get(netValue).times);
  const { rates } = useUsdRates(SNAPSHOT_RATES_DEMAND, times);

  watchImmediate(rates, (resolved) => {
    const next = new Map<number, ResolvedPrice>();
    const snapshotTimes = get(times);
    for (const [index, rate] of resolved.entries())
      next.set(snapshotTimes[index], rate);

    const current = get(snapshotRates);
    if (current.size === next.size && [...next].every(([time, rate]) => sameRate(current.get(time), rate)))
      return;
    store.setSnapshotRates(next);
  });
}
