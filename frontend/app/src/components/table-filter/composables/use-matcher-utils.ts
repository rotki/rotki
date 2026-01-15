import type { ComputedRef, Ref } from 'vue';
import type { SearchMatcher } from '@/types/filtering';

interface UseMatcherUtilsReturn {
  validKeys: ComputedRef<string[]>;
  matcherForKey: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined;
  matcherForKeyValue: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined;
}

export function useMatcherUtils(
  matchers: Ref<SearchMatcher<any, any>[]>,
): UseMatcherUtilsReturn {
  const validKeys = computed<string[]>(() => get(matchers).map(({ key }) => key));

  function matcherForKey(searchKey: string | undefined): SearchMatcher<any, any> | undefined {
    return get(matchers).find(({ key }) => key === searchKey);
  }

  function matcherForKeyValue(searchKey: string | undefined): SearchMatcher<any, any> | undefined {
    return get(matchers).find(({ keyValue }) => keyValue === searchKey);
  }

  return {
    matcherForKey,
    matcherForKeyValue,
    validKeys,
  };
}
