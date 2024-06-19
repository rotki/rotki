import type { BigNumber } from '@rotki/common';
import type { Collection, CollectionResponse } from '@/types/collection';
import type { TablePagination } from '@/types/pagination';

type Entries = 'entries' | 'entriesFound' | 'entriesLimit' | 'entriesTotal';

export function mapCollectionResponse<T, C extends CollectionResponse<T>>(response: C): Collection<T> & Omit<C, Entries> {
  const { entries, entriesLimit, entriesFound, entriesTotal, ...rest }
    = response;
  return {
    data: entries,
    found: entriesFound,
    limit: entriesLimit,
    total: entriesTotal,
    ...rest,
  };
}

export function defaultCollectionState<T>(): Collection<T> {
  return {
    found: 0,
    limit: 0,
    data: [],
    total: 0,
    totalUsdValue: Zero,
  };
}

type TotalValue = BigNumber | undefined | null;

export function getCollectionData<T>(collection: Ref<Collection<T>>): {
  data: ComputedRef<T[]>;
  limit: ComputedRef<number>;
  found: ComputedRef<number>;
  total: ComputedRef<number>;
  entriesFoundTotal: ComputedRef<number | undefined>;
  totalUsdValue: ComputedRef<TotalValue>;
} {
  const data: ComputedRef<T[]> = computed(() => get(collection).data);
  const limit: ComputedRef<number> = computed(() => get(collection).limit);
  const found: ComputedRef<number> = computed(() => get(collection).found);
  const total: ComputedRef<number> = computed(() => get(collection).total);
  const entriesFoundTotal: ComputedRef<number | undefined> = computed(
    () => get(collection).entriesFoundTotal,
  );
  const totalUsdValue: ComputedRef<TotalValue> = computed(
    () => get(collection).totalUsdValue,
  );

  return {
    data,
    limit,
    found,
    total,
    entriesFoundTotal,
    totalUsdValue,
  };
}

export function setupEntryLimit(limit: Ref<number>, found: Ref<number>, total: Ref<number>, entryFoundTotal?: Ref<number | undefined>): {
  itemLength: ComputedRef<number>;
  showUpgradeRow: ComputedRef<boolean>;
} {
  const premium = usePremium();

  const itemLength: ComputedRef<number> = computed(() => {
    const isPremium = get(premium);
    const totalFound = get(found);
    const entryLimit = get(limit);

    if (isPremium || entryLimit === -1)
      return totalFound;

    return Math.min(totalFound, entryLimit);
  });

  const showUpgradeRow: ComputedRef<boolean> = computed(() => {
    if (isDefined(entryFoundTotal))
      return get(found) < get(entryFoundTotal)!;

    return get(limit) <= get(total) && get(limit) > 0;
  });

  return {
    itemLength,
    showUpgradeRow,
  };
}

export function defaultOptions<T extends NonNullable<unknown>>(defaultSortBy?: {
  key?: keyof T | (keyof T)[];
  ascending?: boolean[];
}): TablePagination<T> {
  const { itemsPerPage } = useFrontendSettingsStore();
  const sortByKey = defaultSortBy?.key;
  return {
    page: 1,
    itemsPerPage,
    sortBy: sortByKey
      ? Array.isArray(sortByKey) ? sortByKey : [sortByKey]
      : ['timestamp' as keyof T],
    sortDesc: defaultSortBy?.ascending
      ? defaultSortBy?.ascending.map(bool => !bool)
      : [true],
    singleSort: sortByKey ? !Array.isArray(sortByKey) : false,
  };
}
