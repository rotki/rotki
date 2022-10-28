import { Ref } from 'vue';
import { usePremium } from '@/composables/premium';
import { Collection, CollectionResponse } from '@/types/collection';

export const mapCollectionResponse = <T>(
  response: CollectionResponse<T>
): Collection<T> => {
  return {
    data: response.entries,
    found: response.entriesFound,
    limit: response.entriesLimit,
    total: response.entriesTotal
  };
};

export const defaultCollectionState = <T>(): Collection<T> => ({
  found: 0,
  limit: 0,
  data: [],
  total: 0
});

export const getCollectionData = <T>(collection: Ref<Collection<T>>) => {
  const data = computed<T[]>(() => {
    return get(collection).data as T[];
  });
  const limit = computed<number>(() => get(collection).limit);
  const found = computed<number>(() => get(collection).found);
  const total = computed<number>(() => get(collection).total);

  return {
    data,
    limit,
    found,
    total
  };
};

export const setupEntryLimit = (
  limit: Ref<number>,
  found: Ref<number>,
  total: Ref<number>
) => {
  const premium = usePremium();

  const itemLength = computed(() => {
    const isPremium = get(premium);
    const totalFound = get(found);
    if (isPremium) {
      return totalFound;
    }

    const entryLimit = get(limit);
    return Math.min(totalFound, entryLimit);
  });

  const showUpgradeRow = computed(() => {
    return get(limit) <= get(total) && get(limit) > 0;
  });

  return {
    itemLength,
    showUpgradeRow
  };
};
