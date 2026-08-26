import type { ComputedRef, Ref } from 'vue';
import type { WritableRef } from '@/modules/core/common/common-types';
import { type BigNumber, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

/**
 * A single row in the snapshot list, derived from the net-value series.
 *
 * @remarks
 * Rows are USD-only on purpose. The historic conversion to fiat happens lazily in the display
 * layer, `SnapshotFiatDisplay` and `SnapshotDeltaDisplay`, which render only the visible page.
 * Converting the whole series here instead puts thousands of timestamps through the shared
 * 500-entry LRU on every mount; keeping this derivation pure collapses the working set to one page.
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
 * Sources the snapshot list from the existing `/statistics/netvalue` series, with no per-snapshot
 * round-trips.
 *
 * @remarks
 * The series is USD-denominated, and each row's net worth and Δ are converted at the historic rate
 * of its own timestamp through the lazy, auto-batching historic-price cache.
 *
 * @param filters - the filter state to apply. The list page owns this ref and syncs it to the URL
 * query; the detail page passes its own unfiltered ref so prev/next spans every snapshot. Must be
 * writable: it is returned and two-way bound by the filter controls.
 */
export function useSnapshotList(filters: WritableRef<SnapshotListFilters> = ref({})): UseSnapshotListReturn {
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
