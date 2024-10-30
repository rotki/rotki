import type { BigNumber } from '@rotki/common';
import type { Collection, CollectionResponse } from '@/types/collection';
import type { ComputedRef, Ref } from 'vue';

type Entries = 'entries' | 'entriesFound' | 'entriesLimit' | 'entriesTotal' | 'totalUsdValue';

export function mapCollectionResponse<T, C extends CollectionResponse<T>>(
  response: C,
): Collection<T> & Omit<C, Entries> {
  const { entries, entriesLimit, entriesFound, entriesTotal, totalUsdValue, ...rest } = response;
  return {
    data: entries,
    found: entriesFound,
    limit: entriesLimit,
    total: entriesTotal,
    totalValue: totalUsdValue,
    ...rest,
  };
}

export function defaultCollectionState<T>(): Collection<T> {
  return {
    found: 0,
    limit: 0,
    data: [],
    total: 0,
    totalValue: Zero,
  };
}

type TotalValue = BigNumber | undefined | null;

interface CollectionData<T> {
  data: ComputedRef<T[]>;
  limit: ComputedRef<number>;
  found: ComputedRef<number>;
  total: ComputedRef<number>;
  entriesFoundTotal: ComputedRef<number | undefined>;
  totalValue: ComputedRef<TotalValue>;
}

export function getCollectionData<T>(collection: Ref<Collection<T>>): CollectionData<T> {
  const data = computed<T[]>(() => get(collection).data);
  const limit = computed<number>(() => get(collection).limit);
  const found = computed<number>(() => get(collection).found);
  const total = computed<number>(() => get(collection).total);
  const entriesFoundTotal = computed<number | undefined>(() => get(collection).entriesFoundTotal);
  const totalValue = computed<TotalValue>(() => get(collection).totalValue);

  return {
    data,
    limit,
    found,
    total,
    entriesFoundTotal,
    totalValue,
  };
}

export function setupEntryLimit(
  limit: Ref<number>,
  found: Ref<number>,
  total: Ref<number>,
  entryFoundTotal?: Ref<number | undefined>,
): {
    itemLength: ComputedRef<number>;
    showUpgradeRow: ComputedRef<boolean>;
  } {
  const premium = usePremium();

  const itemLength = computed<number>(() => {
    const isPremium = get(premium);
    const totalFound = get(found);
    const entryLimit = get(limit);

    if (isPremium || entryLimit === -1)
      return totalFound;

    return Math.min(totalFound, entryLimit);
  });

  const showUpgradeRow = computed<boolean>(() => {
    if (isDefined(entryFoundTotal))
      return get(found) < get(entryFoundTotal)!;

    return get(limit) <= get(total) && get(limit) > 0;
  });

  return {
    itemLength,
    showUpgradeRow,
  };
}
