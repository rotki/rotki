import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { HistoricalAssetRow } from '@/modules/statistics/historical-balances/use-historical-balance-values';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useCollectionInfo } from '@/modules/assets/use-collection-info';
import {
  filterRows,
  type HistoricalBalanceRow,
  HistoricalBalancesMode,
  type HistoricalBalancesSummary,
  summarize,
  toViewRows,
} from '@/modules/statistics/historical-balances/historical-balances-view';

interface UseHistoricalBalancesViewReturn {
  /** The rows the table shows, filtered and in the chosen mode. */
  rows: ComputedRef<HistoricalBalanceRow[]>;
  /** The total and counts of the filtered rows. */
  summary: ComputedRef<HistoricalBalancesSummary>;
  /** Every location on the day, for the location filter. */
  locations: ComputedRef<string[]>;
  /** Every account on the day, for the account filter. */
  accounts: ComputedRef<string[]>;
  /** Any filter is narrowing the rows. */
  filtered: ComputedRef<boolean>;
  modelLocations: Ref<string[]>;
  modelAccounts: Ref<string[]>;
  modelSearch: Ref<string>;
  modelMode: Ref<HistoricalBalancesMode>;
}

function distinctSorted(values: Iterable<string>): string[] {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b));
}

/**
 * Filters the priced rows by location, account and asset, and folds asset collections.
 *
 * @remarks
 * Both steps run on rows that are already priced, so neither a filter nor the mode asks for a price
 * again. The summary follows the filter but not the mode: a collection folds rows without changing
 * what they add up to, and the counts name assets, not rows. The asset search matches the symbol,
 * name or identifier of each asset, so it finds a collection by any of its members.
 *
 * @param rows - the priced rows of the day
 */
export function useHistoricalBalancesView(rows: MaybeRefOrGetter<HistoricalAssetRow[]>): UseHistoricalBalancesViewReturn {
  const modelLocations = ref<string[]>([]);
  const modelAccounts = ref<string[]>([]);
  const modelSearch = shallowRef<string>('');
  const modelMode = shallowRef<HistoricalBalancesMode>(HistoricalBalancesMode.COLLECTION);

  const search = refDebounced(modelSearch, 200);

  const { getAssetInfo } = useAssetInfoRetrieval();
  const { getCollectionId, getCollectionMainAsset } = useCollectionInfo();

  function matchesSearch(query: string): (asset: string) => boolean {
    return (asset: string): boolean => {
      const info = getAssetInfo(asset);
      return [asset, info?.symbol, info?.name].some(text => text?.toLocaleLowerCase().includes(query));
    };
  }

  const locations = computed<string[]>(() =>
    distinctSorted(toValue(rows).flatMap(row => row.buckets.map(bucket => bucket.location))));

  const accounts = computed<string[]>(() =>
    distinctSorted(toValue(rows).flatMap(row => row.buckets.flatMap(bucket => bucket.locationLabel ?? []))));

  const filteredRows = computed<HistoricalAssetRow[]>(() => {
    const query = get(search).trim().toLocaleLowerCase();
    return filterRows(toValue(rows), {
      accounts: get(modelAccounts),
      locations: get(modelLocations),
      matchesAsset: query ? matchesSearch(query) : undefined,
    });
  });

  const filtered = computed<boolean>(() =>
    get(modelLocations).length > 0 || get(modelAccounts).length > 0 || get(search).trim().length > 0);

  const viewRows = computed<HistoricalBalanceRow[]>(() => toViewRows(get(filteredRows), get(modelMode), {
    collectionOf: getCollectionId,
    mainAssetOf: getCollectionMainAsset,
  }));

  const summary = computed<HistoricalBalancesSummary>(() => summarize(get(filteredRows)));

  return {
    accounts,
    filtered,
    locations,
    modelAccounts,
    modelLocations,
    modelMode,
    modelSearch,
    rows: viewRows,
    summary,
  };
}
