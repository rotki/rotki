import type { AccountHistoryRange, AccountHistorySelection } from '@/modules/balances/account-history/account-history-selection';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type DeepReadonly, type Ref, type WritableComputedRef } from 'vue';
import {
  type BalancePoint,
  type BalanceSummary,
  bucketLocations,
  type BucketSeries,
  type SeriesRange,
  summarize,
  totalSeries,
} from '@/modules/balances/account-history/balance-series';
import { useAccountAssets } from '@/modules/balances/account-history/use-account-assets';
import { useAccountBalanceSeries } from '@/modules/balances/account-history/use-account-balance-series';
import { useAccountHistorySelection } from '@/modules/balances/account-history/use-account-history-selection';

interface UseAccountHistoryReturn {
  selection: ComputedRef<AccountHistorySelection>;
  modelAccount: WritableComputedRef<string | undefined>;
  modelAsset: WritableComputedRef<string | undefined>;
  modelLocation: WritableComputedRef<string | undefined>;
  modelRange: WritableComputedRef<AccountHistoryRange>;
  assets: ComputedRef<string[]>;
  assetsLoading: DeepReadonly<Ref<boolean>>;
  /** The account's events are not all processed, so the asset list may be short. */
  assetsProcessingRequired: DeepReadonly<Ref<boolean>>;
  /** The locations the account holds the asset in, for the location picker. */
  locations: ComputedRef<string[]>;
  /** The buckets in the picked location, or in every location when none is picked. */
  buckets: ComputedRef<BucketSeries[]>;
  total: ComputedRef<BalancePoint[]>;
  summary: ComputedRef<BalanceSummary>;
  loadedRange: DeepReadonly<Ref<SeriesRange | undefined>>;
  loading: DeepReadonly<Ref<boolean>>;
  error: ComputedRef<string | undefined>;
  processingRequired: DeepReadonly<Ref<boolean>>;
  /** An account and asset are picked, the series loaded, and nothing was held in the range. */
  empty: ComputedRef<boolean>;
  refresh: () => Promise<void>;
}

/**
 * Everything the account history page shows, derived from the selection in the route query.
 *
 * @remarks
 * The series is always loaded for every location, and the location pick filters it here: the
 * picker's options come from the same load, so narrowing by location needs no second request and
 * never offers a location with nothing to show.
 */
export function useAccountHistory(): UseAccountHistoryReturn {
  const { modelAccount, modelAsset, modelLocation, modelRange, selection } = useAccountHistorySelection();

  const {
    assets,
    error: assetsError,
    loading: assetsLoading,
    processingRequired: assetsProcessingRequired,
  } = useAccountAssets(() => get(selection).account);
  const {
    buckets: allBuckets,
    error: seriesError,
    loadedRange,
    loading,
    processingRequired,
    refresh,
  } = useAccountBalanceSeries({
    account: () => get(selection).account,
    asset: () => get(selection).asset,
    range: () => get(selection).range,
  });

  const locations = computed<string[]>(() => bucketLocations(get(allBuckets)));

  const buckets = computed<BucketSeries[]>(() => {
    const location = get(selection).location;
    const all = get(allBuckets);
    return location ? all.filter(bucket => bucket.location === location) : all;
  });

  const total = computed<BalancePoint[]>(() => totalSeries(get(buckets)));

  const summary = computed<BalanceSummary>(() => summarize(get(total), get(loadedRange)?.from ?? 0));

  const error = computed<string | undefined>(() => get(seriesError) ?? get(assetsError));

  const empty = computed<boolean>(() => {
    const { account, asset } = get(selection);
    return !!account && !!asset && !get(loading) && !get(error) && !!get(loadedRange) && get(buckets).length === 0;
  });

  return {
    assets,
    assetsLoading,
    assetsProcessingRequired,
    buckets,
    empty,
    error,
    loadedRange,
    loading,
    locations,
    modelAccount,
    modelAsset,
    modelLocation,
    modelRange,
    processingRequired,
    refresh,
    selection,
    summary,
    total,
  };
}
