import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { SearchMatcher, Suggestion } from '@/modules/core/table/filtering';
import { getTextToken } from '@rotki/common';
import { compareTextByKeyword } from '@/modules/core/common/display/assets';

interface UseFilterMatchersReturn {
  filteredMatchers: ComputedRef<SearchMatcher<any>[]>;
  usedKeys: ComputedRef<string[]>;
}

export function useFilterMatchers(
  matchers: MaybeRefOrGetter<SearchMatcher<any, any>[]>,
  selection: Ref<Suggestion[]>,
  search: Ref<string>,
): UseFilterMatchersReturn {
  const usedKeys = computed<string[]>(() => get(selection).map(entry => entry.key));

  const filteredMatchers = computed<SearchMatcher<any>[]>(() => {
    const filteredByUsedKeys = toValue(matchers).filter(({ key, multiple }) => !get(usedKeys).includes(key) || multiple);

    const searchVal = get(search);
    if (!searchVal)
      return filteredByUsedKeys;

    const searchToken = getTextToken(searchVal);

    const filteredByKey = filteredByUsedKeys
      .filter(({ key }) => getTextToken(key).includes(searchToken))
      .sort((a, b) => compareTextByKeyword(getTextToken(a.key), getTextToken(b.key), searchToken));

    const keySet = new Set(filteredByKey.map(item => item.key));

    const filteredByDescription = filteredByUsedKeys
      .filter(({ description, key }) => !keySet.has(key) && getTextToken(description).includes(searchToken))
      .sort((a, b) => compareTextByKeyword(getTextToken(a.description), getTextToken(b.description), searchToken));

    return [...filteredByKey, ...filteredByDescription];
  });

  return {
    filteredMatchers,
    usedKeys,
  };
}
