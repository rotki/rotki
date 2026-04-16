import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { SearchMatcher } from '@/modules/core/table/filtering';

interface UseMatcherUtilsReturn {
  validKeys: ComputedRef<string[]>;
  matcherForKey: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined;
  matcherForKeyValue: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined;
}

export function useMatcherUtils(
  matchers: MaybeRefOrGetter<SearchMatcher<any, any>[]>,
): UseMatcherUtilsReturn {
  const validKeys = computed<string[]>(() => toValue(matchers).map(({ key }) => key));

  function matcherForKey(searchKey: string | undefined): SearchMatcher<any, any> | undefined {
    return toValue(matchers).find(({ key }) => key === searchKey);
  }

  function matcherForKeyValue(searchKey: string | undefined): SearchMatcher<any, any> | undefined {
    return toValue(matchers).find(({ keyValue }) => keyValue === searchKey);
  }

  return {
    matcherForKey,
    matcherForKeyValue,
    validKeys,
  };
}
