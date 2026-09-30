import type { ComputedRef, DeepReadonly, MaybeRefOrGetter, Ref } from 'vue';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';
import { groupByAsset, type HistoricalAssetGroup } from '@/modules/statistics/historical-balances/historical-balances-grouping';

interface UseHistoricalBalancesAtReturn {
  groups: ComputedRef<HistoricalAssetGroup[]>;
  /**
   * The timestamp `groups` were loaded for, in unix seconds. It trails the requested one while a
   * load is in flight, so the rows shown are always labelled and priced for their own day.
   */
  loadedAt: DeepReadonly<Ref<number | undefined>>;
  loading: DeepReadonly<Ref<boolean>>;
  /** The last load failed; the reason, for display. */
  error: DeepReadonly<Ref<string | undefined>>;
  /** Events exist that the backend has not replayed yet, so the balances may be behind. */
  processingRequired: DeepReadonly<Ref<boolean>>;
  empty: ComputedRef<boolean>;
  refresh: () => Promise<void>;
}

/**
 * Loads every account's balances at a timestamp, grouped by asset.
 *
 * @remarks
 * Reloads when the timestamp changes, when a history sync settles, since new events can change any
 * past balance, and when the backend finishes replaying events into balances. A load that finishes
 * after a newer one started is dropped, so a quick change of date never shows the earlier date's
 * balances.
 *
 * @param timestamp - unix seconds
 */
export function useHistoricalBalancesAt(timestamp: MaybeRefOrGetter<number>): UseHistoricalBalancesAtReturn {
  const loaded = shallowRef<HistoricalAssetGroup[]>([]);
  const loadedAt = shallowRef<number>();
  const loading = shallowRef<boolean>(false);
  const error = ref<string>();
  const processingRequired = shallowRef<boolean>(false);

  const { historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  const { fetchHistoricalBalances } = useHistoricalBalancesApi();
  const { syncCompleted } = useSyncCompleted();

  let latestRequest = 0;

  /** Read-only without `readonly()`, whose deep type would make every `BigNumber` in a group unusable. */
  const groups = computed<HistoricalAssetGroup[]>(() => get(loaded));

  const empty = computed<boolean>(() => !get(loading) && !get(error) && get(groups).length === 0);

  async function refresh(): Promise<void> {
    const request = ++latestRequest;
    const at = toValue(timestamp);
    set(loading, true);
    set(error, undefined);
    try {
      const response = await fetchHistoricalBalances(at);
      if (request !== latestRequest)
        return;
      set(loaded, groupByAsset(response.entries));
      set(loadedAt, at);
      set(processingRequired, response.processingRequired);
    }
    catch (error_: unknown) {
      if (request !== latestRequest)
        return;
      logger.error(error_);
      set(loaded, []);
      set(loadedAt, at);
      set(processingRequired, false);
      set(error, error_ instanceof Error ? error_.message : String(error_));
    }
    finally {
      if (request === latestRequest)
        set(loading, false);
    }
  }

  watchImmediate(() => toValue(timestamp), refresh);
  watch(syncCompleted, refresh);
  watch(historicalBalanceProcessingCompleted, refresh);

  return {
    empty,
    error: readonly(error),
    groups,
    loadedAt: readonly(loadedAt),
    loading: readonly(loading),
    processingRequired: readonly(processingRequired),
    refresh,
  };
}
