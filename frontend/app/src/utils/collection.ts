import type { Collection, CollectionResponse } from '@/types/collection';
import type { ComputedRef, Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { type BigNumber, Zero } from '@rotki/common';

type Entries = 'entries' | 'entriesFound' | 'entriesLimit' | 'entriesTotal';

export function mapCollectionResponse<T, C extends CollectionResponse<T>>(
  response: C,
): Collection<T> & Omit<C, Entries> {
  const { entries, entriesFound, entriesLimit, entriesTotal, ...rest } = response;
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
    data: [],
    found: 0,
    limit: 0,
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
  const data = computed<T[]>(() => get(collection).data);
  const limit = computed<number>(() => get(collection).limit);
  const found = computed<number>(() => get(collection).found);
  const total = computed<number>(() => get(collection).total);
  const entriesFoundTotal = computed<number | undefined>(() => get(collection).entriesFoundTotal);
  const totalUsdValue = computed<TotalValue>(() => get(collection).totalUsdValue);

  return {
    data,
    entriesFoundTotal,
    found,
    limit,
    total,
    totalUsdValue,
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
