import type { ComputedRef, Ref } from 'vue';
import { type BigNumber, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

/**
 * A single row in the snapshot list, derived from the net-value series.
 *
 * Rows are intentionally USD-only: the historic USD->fiat conversion (#12277)
 * happens lazily in the display layer (`SnapshotFiatDisplay` /
 * `SnapshotDeltaDisplay`), which is rendered only for the visible page. Eagerly
 * converting the whole series here used to hammer the historic-rate endpoint —
 * thousands of timestamps thrashing the shared 500-entry LRU on every mount.
 * Keeping this derivation pure collapses the working set to one page.
 */
export interface SnapshotListRow {
  /** Snapshot timestamp in SECONDS (net-value series / historic-cache unit). */
  timestamp: number;
  /** The stored net worth at this snapshot, denominated in USD. */
  usdValue: BigNumber;
  /**
   * The timestamp (seconds) of the chronologically previous snapshot, used by
   * the display layer to compute the per-row Δ. `undefined` for the oldest.
   */
  previousTimestamp?: number;
  /** The USD net worth of the chronologically previous snapshot (for the Δ). */
  previousUsdValue?: BigNumber;
}

export interface SnapshotListFilters {
  /** Inclusive lower bound (seconds), or `undefined` for no lower bound. */
  fromTimestamp?: number;
  /** Inclusive upper bound (seconds), or `undefined` for no upper bound. */
  toTimestamp?: number;
}

interface UseSnapshotListReturn {
  rows: ComputedRef<SnapshotListRow[]>;
  /** Whether any snapshot exists at all, ignoring the active range filter. */
  hasSnapshots: ComputedRef<boolean>;
  loading: Readonly<Ref<boolean>>;
  filters: Ref<SnapshotListFilters>;
  refresh: () => Promise<void>;
}

/**
 * Sources the snapshot list from the existing `/statistics/netvalue` series
 * (no per-snapshot round-trips). The series is USD-denominated; each row's net
 * worth and Δ are converted at the historic USD->fiat rate of its own timestamp
 * via the lazy, auto-batching historic-price cache.
 *
 * @param filters the filter state to apply. The list page owns this ref and syncs
 *   it to the URL query; the detail page omits it (its own unfiltered ref) so its
 *   prev/next navigation spans every snapshot. Must be a writable ref — it is
 *   returned and two-way bound by the filter controls.
 */
// eslint-disable-next-line @rotki/composable-input-flexibility
export function useSnapshotList(filters: Ref<SnapshotListFilters> = ref({})): UseSnapshotListReturn {
  const { netValue } = storeToRefs(useStatisticsStore());
  const { fetchNetValue } = useStatisticsDataFetching();

  const loading = shallowRef<boolean>(false);

  // Pure USD-only derivation: no historic-rate lookups here. Each row carries
  // its chronological predecessor (from the full series, before any range
  // filter) so the display layer can compute the Δ for just the visible rows.
  const baseRows = computed<SnapshotListRow[]>(() => {
    const { data, times } = get(netValue);
    const rows: SnapshotListRow[] = [];

    let previousTimestamp: number | undefined;
    let previousUsdValue: BigNumber | undefined;

    for (const [index, timestamp] of times.entries()) {
      const usdValue = data[index] ?? Zero;

      rows.push({ previousTimestamp, previousUsdValue, timestamp, usdValue });

      previousTimestamp = timestamp;
      previousUsdValue = usdValue;
    }

    return rows;
  });

  const hasSnapshots = computed<boolean>(() => get(baseRows).length > 0);

  const rows = computed<SnapshotListRow[]>(() => {
    const { fromTimestamp, toTimestamp } = get(filters);

    return get(baseRows).filter((row) => {
      if (fromTimestamp !== undefined && row.timestamp < fromTimestamp)
        return false;
      if (toTimestamp !== undefined && row.timestamp > toTimestamp)
        return false;
      return true;
    });
  });

  async function refresh(): Promise<void> {
    set(loading, true);
    try {
      await fetchNetValue();
    }
    finally {
      set(loading, false);
    }
  }

  // Reuse the cached net-value series across navigation: only fetch on first
  // load (empty series). The Refresh button, take-snapshot and post-delete paths
  // keep it fresh, so re-fetching on every mount would just churn the UI (and the
  // historic-rate lookups) for no benefit.
  onMounted(() => {
    if (get(netValue).times.length === 0)
      startPromise(refresh());
  });

  return {
    // The caller's own ref, returned for two-way binding by the filter controls.
    filters,
    hasSnapshots,
    loading: readonly(loading),
    refresh,
    rows,
  };
}
