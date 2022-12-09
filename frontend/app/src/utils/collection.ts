import { type BigNumber } from '@rotki/common';
import { type ComputedRef, type Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { type Collection, type CollectionResponse } from '@/types/collection';
import { Zero } from '@/utils/bignumbers';

export const mapCollectionResponse = <T>(
  response: CollectionResponse<T>
): Collection<T> => {
  return {
    data: response.entries,
    found: response.entriesFound,
    limit: response.entriesLimit,
    total: response.entriesTotal,
    totalUsdValue: response.totalUsdValue
  };
};

export const defaultCollectionState = <T>(): Collection<T> => ({
  found: 0,
  limit: 0,
  data: [],
  total: 0,
  totalUsdValue: Zero
});

type TotalValue = BigNumber | undefined | null;

export const getCollectionData = <T>(
  collection: Ref<Collection<T>>
): {
  data: ComputedRef<T[]>;
  limit: ComputedRef<number>;
  found: ComputedRef<number>;
  total: ComputedRef<number>;
  totalUsdValue: ComputedRef<TotalValue>;
} => {
  const data: ComputedRef<T[]> = computed(() => get(collection).data);
  const limit: ComputedRef<number> = computed(() => get(collection).limit);
  const found: ComputedRef<number> = computed(() => get(collection).found);
  const total: ComputedRef<number> = computed(() => get(collection).total);
  const totalUsdValue: ComputedRef<TotalValue> = computed(
    () => get(collection).totalUsdValue
  );

  return {
    data,
    limit,
    found,
    total,
    totalUsdValue
  };
};

export const setupEntryLimit = (
  limit: Ref<number>,
  found: Ref<number>,
  total: Ref<number>
): {
  itemLength: ComputedRef<number>;
  showUpgradeRow: ComputedRef<boolean>;
} => {
  const premium = usePremium();

  const itemLength: ComputedRef<number> = computed(() => {
    const isPremium = get(premium);
    const totalFound = get(found);
    if (isPremium) {
      return totalFound;
    }

    const entryLimit = get(limit);
    return Math.min(totalFound, entryLimit);
  });

  const showUpgradeRow: ComputedRef<boolean> = computed(() => {
    return get(limit) <= get(total) && get(limit) > 0;
  });

  return {
    itemLength,
    showUpgradeRow
  };
};
