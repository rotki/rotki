import type { SearchMatcher, StringSuggestionMatcher, Suggestion } from '@/types/filtering';
import { get } from '@vueuse/shared';
import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { useFilterMatchers } from '@/components/table-filter/composables/use-filter-matchers';

describe('composables/use-filter-matchers', () => {
  function createStringMatcher(key: string, keyValue?: string): StringSuggestionMatcher<string, string> {
    return {
      description: `filter by ${key}`,
      key,
      keyValue: keyValue ?? key,
      multiple: true,
      string: true,
      suggestions: () => [`${key} 1`, `${key} 2`],
      validate: () => true,
    };
  }

  function createSuggestion(key: string, value: string): Suggestion {
    return {
      asset: false,
      index: 0,
      key,
      total: 1,
      value,
    };
  }

  describe('usedKeys', () => {
    it('returns keys from selection', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([]);
      const selection = ref<Suggestion[]>([
        createSuggestion('type', 'value1'),
        createSuggestion('status', 'active'),
      ]);
      const search = ref<string>('');

      const { usedKeys } = useFilterMatchers(matchers, selection, search);

      expect(get(usedKeys)).toEqual(['type', 'status']);
    });

    it('returns empty array for empty selection', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([]);
      const selection = ref<Suggestion[]>([]);
      const search = ref<string>('');

      const { usedKeys } = useFilterMatchers(matchers, selection, search);

      expect(get(usedKeys)).toEqual([]);
    });
  });

  describe('filteredMatchers', () => {
    it('returns all matchers when search is empty', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
        createStringMatcher('status'),
      ]);
      const selection = ref<Suggestion[]>([]);
      const search = ref<string>('');

      const { filteredMatchers } = useFilterMatchers(matchers, selection, search);

      expect(get(filteredMatchers)).toHaveLength(2);
    });

    it('excludes used non-multiple matchers', () => {
      const nonMultipleMatcher: StringSuggestionMatcher<string, string> = {
        description: 'filter by single',
        key: 'single',
        keyValue: 'single',
        multiple: false,
        string: true,
        suggestions: () => [],
        validate: () => true,
      };
      const matchers = ref<SearchMatcher<any, any>[]>([
        nonMultipleMatcher,
        createStringMatcher('type'),
      ]);
      const selection = ref<Suggestion[]>([
        createSuggestion('single', 'value'),
      ]);
      const search = ref<string>('');

      const { filteredMatchers } = useFilterMatchers(matchers, selection, search);

      expect(get(filteredMatchers)).toHaveLength(1);
      expect(get(filteredMatchers)[0].key).toBe('type');
    });

    it('includes used multiple matchers', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
      ]);
      const selection = ref<Suggestion[]>([
        createSuggestion('type', 'value1'),
      ]);
      const search = ref<string>('');

      const { filteredMatchers } = useFilterMatchers(matchers, selection, search);

      expect(get(filteredMatchers)).toHaveLength(1);
    });

    it('filters by key when search matches', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
        createStringMatcher('status'),
      ]);
      const selection = ref<Suggestion[]>([]);
      const search = ref<string>('typ');

      const { filteredMatchers } = useFilterMatchers(matchers, selection, search);

      expect(get(filteredMatchers)).toHaveLength(1);
      expect(get(filteredMatchers)[0].key).toBe('type');
    });

    it('filters by description when search matches', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('foo'),
        createStringMatcher('bar'),
      ]);
      const selection = ref<Suggestion[]>([]);
      const search = ref<string>('filter by foo');

      const { filteredMatchers } = useFilterMatchers(matchers, selection, search);

      expect(get(filteredMatchers)).toHaveLength(1);
      expect(get(filteredMatchers)[0].key).toBe('foo');
    });
  });
});
