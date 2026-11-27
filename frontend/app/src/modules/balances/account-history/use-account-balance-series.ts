import { watchImmediate } from '@vueuse/core';
import { get, set } from '@vueuse/shared';
import dayjs from 'dayjs';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type DeepReadonly, type MaybeRefOrGetter, readonly, type Ref, shallowRef, toValue, watch } from 'vue';
import { type AccountHistoryRange, rangeStart } from '@/modules/balances/account-history/account-history-selection';
import { type BucketSeries, buildBucketSeries, type SeriesRange } from '@/modules/balances/account-history/balance-series';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

interface AccountBalanceSeriesOptions {
  account: MaybeRefOrGetter<string | undefined>;
  asset: MaybeRefOrGetter<string | undefined>;
  range: MaybeRefOrGetter<AccountHistoryRange>;
}

interface UseAccountBalanceSeriesReturn {
  buckets: ComputedRef<BucketSeries[]>;
  /** The range `buckets` were loaded for; absent until the first load lands. */
  loadedRange: DeepReadonly<Ref<SeriesRange | undefined>>;
  loading: DeepReadonly<Ref<boolean>>;
  error: DeepReadonly<Ref<string | undefined>>;
  /** Events in the range are not replayed into balances yet, so the series may be behind. */
  processingRequired: DeepReadonly<Ref<boolean>>;
  refresh: () => Promise<void>;
}

/**
 * Loads one account's balance series of one asset over a range, one series per bucket.
 *
 * @remarks
 * A bounded range also loads the balances just before it, which start each bucket's line. Picking
 * another account or asset clears what is shown, since it belongs to the previous pick; a reload of
 * the same pick (another range, a finished sync or processing run) keeps it on screen until the new
 * series lands. A load that finishes after a newer one started is dropped.
 */
export function useAccountBalanceSeries(options: AccountBalanceSeriesOptions): UseAccountBalanceSeriesReturn {
  const { account, asset, range } = options;
  const loaded = shallowRef<BucketSeries[]>([]);
  const loadedRange = shallowRef<SeriesRange>();
  const loading = shallowRef<boolean>(false);
  const error = shallowRef<string>();
  const processingRequired = shallowRef<boolean>(false);

  const { historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  const { fetchBalanceSeries, fetchHistoricalBalances } = useHistoricalBalancesApi();
  const { syncCompleted } = useSyncCompleted();

  let latestRequest = 0;

  function clear(): void {
    set(loaded, []);
    set(loadedRange, undefined);
    set(processingRequired, false);
    set(error, undefined);
  }

  async function refresh(): Promise<void> {
    const request = ++latestRequest;
    const locationLabel = toValue(account);
    const assetId = toValue(asset);
    if (!locationLabel || !assetId) {
      clear();
      set(loading, false);
      return;
    }

    const to = dayjs().unix();
    const from = rangeStart(toValue(range), to);
    set(loading, true);
    set(error, undefined);
    try {
      const [series, opening] = await Promise.all([
        fetchBalanceSeries({ asset: assetId, fromTimestamp: from, locationLabel, toTimestamp: to }),
        from > 0
          ? fetchHistoricalBalances(from - 1, { asset: assetId, locationLabel })
          : Promise.resolve({ entries: [], processingRequired: false }),
      ]);
      if (request !== latestRequest)
        return;
      set(loaded, buildBucketSeries(opening.entries, series.entries, { from, to }));
      set(loadedRange, { from, to });
      set(processingRequired, series.processingRequired || opening.processingRequired);
    }
    catch (error_: unknown) {
      if (request !== latestRequest)
        return;
      logger.error(error_);
      clear();
      set(error, error_ instanceof Error ? error_.message : String(error_));
    }
    finally {
      if (request === latestRequest)
        set(loading, false);
    }
  }

  watch(() => [toValue(account), toValue(asset)], clear);
  watchImmediate(() => [toValue(account), toValue(asset), toValue(range)], refresh);
  watch(syncCompleted, refresh);
  watch(historicalBalanceProcessingCompleted, refresh);

  return {
    buckets: computed<BucketSeries[]>(() => get(loaded)),
    error: readonly(error),
    loadedRange: readonly(loadedRange),
    loading: readonly(loading),
    processingRequired: readonly(processingRequired),
    refresh,
  };
}
