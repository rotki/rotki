import type { ComputedRef, Ref } from 'vue';
import { type BigNumber, Zero } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

/** A single row in the snapshot list, derived from the net-value series. */
export interface SnapshotListRow {
  /** Snapshot timestamp in SECONDS (net-value series / historic-cache unit). */
  timestamp: number;
  /** The stored net worth at this snapshot, denominated in USD. */
  usdValue: BigNumber;
  /**
   * The net worth converted to the user's display currency at the *historic*
   * rate of this snapshot's timestamp (#12277). Equals `usdValue` when the
   * display currency is USD, or `Zero` while the rate is not yet `ready`.
   */
  fiatValue: BigNumber;
  /**
   * The change in `fiatValue` versus the chronologically previous snapshot.
   * `undefined` for the oldest snapshot, or whenever either side's historic
   * rate is not yet resolved (so a placeholder zero never produces a bogus Δ).
   */
  delta?: BigNumber;
  /** Whether the historic USD->fiat rate for this row is still loading. */
  fiatPending: boolean;
  /**
   * Whether `fiatValue` is usable. `false` while pending, or when the historic
   * rate is permanently missing (lets the table distinguish a skeleton from a
   * "no price" dash).
   */
  ready: boolean;
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
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { createKey, getHistoricPrice, getIsPending } = useHistoricPriceCache();

  const loading = shallowRef<boolean>(false);

  const isUsd = computed<boolean>(() => get(currencySymbol) === CURRENCY_USD);

  /** Converts a single USD net worth to display currency at its historic rate. */
  function convert(timestamp: number, usdValue: BigNumber): Pick<SnapshotListRow, 'fiatPending' | 'fiatValue' | 'ready'> {
    if (get(isUsd))
      return { fiatPending: false, fiatValue: usdValue, ready: true };

    const rate = getHistoricPrice(CURRENCY_USD, timestamp);
    const fiatPending = getIsPending(createKey(CURRENCY_USD, timestamp));
    const ready = rate.isPositive();
    return { fiatPending, fiatValue: ready ? usdValue.multipliedBy(rate) : Zero, ready };
  }

  const baseRows = computed<SnapshotListRow[]>(() => {
    const { data, times } = get(netValue);
    const rows: SnapshotListRow[] = [];

    let prevFiat: BigNumber | undefined;
    let prevReady = false;

    for (const [index, timestamp] of times.entries()) {
      const usdValue = data[index] ?? Zero;
      const { fiatPending, fiatValue, ready } = convert(timestamp, usdValue);

      const delta = index > 0 && ready && prevReady && prevFiat !== undefined
        ? fiatValue.minus(prevFiat)
        : undefined;

      rows.push({ delta, fiatPending, fiatValue, ready, timestamp, usdValue });

      prevFiat = fiatValue;
      prevReady = ready;
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
