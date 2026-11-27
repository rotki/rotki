import { get } from '@vueuse/shared';
import dayjs from 'dayjs';
import { computed, type ComputedRef, type DeepReadonly, type Ref, type WritableComputedRef } from 'vue';
import {
  AccountHistoryRange,
  type AccountHistorySelection,
  rangeStart,
} from '@/modules/balances/account-history/account-history-selection';
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
import { usePremium } from '@/modules/premium/use-premium';

interface UseAccountHistoryReturn {
  selection: ComputedRef<AccountHistorySelection>;
  /** Both an account and an asset are picked. */
  picked: ComputedRef<boolean>;
  /** The balance data needs premium; without it only the events are loaded. */
  premium: Ref<boolean>;
  modelAccount: WritableComputedRef<string | undefined>;
  modelAsset: WritableComputedRef<string | undefined>;
  modelLocation: WritableComputedRef<string | undefined>;
  modelRange: WritableComputedRef<AccountHistoryRange>;
  assets: ComputedRef<string[]>;
  assetsLoading: DeepReadonly<Ref<boolean>>;
  /** The account's events are not all processed, so the asset list may be short. */
  assetsProcessingRequired: DeepReadonly<Ref<boolean>>;
  /** The locations the account held the asset in, for the location pill. */
  locations: ComputedRef<string[]>;
  /** The buckets in the picked location, or in every location when none is picked. */
  buckets: ComputedRef<BucketSeries[]>;
  total: ComputedRef<BalancePoint[]>;
  summary: ComputedRef<BalanceSummary>;
  loadedRange: DeepReadonly<Ref<SeriesRange | undefined>>;
  /**
   * The window the events list shows: the loaded range with premium, so the list matches the chart,
   * and the picked range measured from now without it. Absent for all time.
   */
  eventsRange: ComputedRef<SeriesRange | undefined>;
  loading: DeepReadonly<Ref<boolean>>;
  error: ComputedRef<string | undefined>;
  processingRequired: DeepReadonly<Ref<boolean>>;
  /** The series loaded for a picked account and asset, and nothing was held in the range. */
  empty: ComputedRef<boolean>;
  refresh: () => Promise<void>;
}

/**
 * Everything the account history page shows, derived from the selection in the route query.
 *
 * @remarks
 * The series is always loaded for every location, and the location pick filters it here: the
 * pill's options come from the same load, so narrowing by location needs no second request and
 * never offers a location with nothing to show. Without premium nothing but the events is loaded,
 * since the balance endpoints need it.
 */
export function useAccountHistory(): UseAccountHistoryReturn {
  const { modelAccount, modelAsset, modelLocation, modelRange, selection } = useAccountHistorySelection();
  const premium = usePremium();

  /** The account the balance endpoints are asked about: none without premium, so none are called. */
  const balanceAccount = (): string | undefined => (get(premium) ? get(selection).account : undefined);

  const {
    assets,
    error: assetsError,
    loading: assetsLoading,
    processingRequired: assetsProcessingRequired,
  } = useAccountAssets(balanceAccount);
  const {
    buckets: allBuckets,
    error: seriesError,
    loadedRange,
    loading,
    processingRequired,
    refresh,
  } = useAccountBalanceSeries({
    account: balanceAccount,
    asset: () => get(selection).asset,
    range: () => get(selection).range,
  });

  const picked = computed<boolean>(() => !!get(selection).account && !!get(selection).asset);

  const eventsRange = computed<SeriesRange | undefined>(() => {
    if (get(premium))
      return get(loadedRange);
    const { range } = get(selection);
    if (range === AccountHistoryRange.ALL)
      return undefined;
    const to = dayjs().unix();
    return { from: rangeStart(range, to), to };
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

  // A loaded range implies a picked account and asset: the series clears it when either is unset.
  const empty = computed<boolean>(() => !get(loading) && !get(error) && !!get(loadedRange) && get(buckets).length === 0);

  return {
    assets,
    assetsLoading,
    assetsProcessingRequired,
    buckets,
    empty,
    error,
    eventsRange,
    loadedRange,
    loading,
    locations,
    modelAccount,
    modelAsset,
    modelLocation,
    modelRange,
    picked,
    premium,
    processingRequired,
    refresh,
    selection,
    summary,
    total,
  };
}
