import type { SearchMatcher, StringSuggestionMatcher } from '@/types/filtering';
import { get } from '@vueuse/shared';
import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { useMatcherUtils } from '@/components/table-filter/composables/use-matcher-utils';

describe('composables/use-matcher-utils', () => {
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

  describe('validKeys', () => {
    it('returns all matcher keys', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
        createStringMatcher('status'),
      ]);

      const { validKeys } = useMatcherUtils(matchers);

      expect(get(validKeys)).toEqual(['type', 'status']);
    });

    it('returns empty array for no matchers', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([]);

      const { validKeys } = useMatcherUtils(matchers);

      expect(get(validKeys)).toEqual([]);
    });
  });

  describe('matcherForKey', () => {
    it('finds matcher by key', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
        createStringMatcher('status'),
      ]);

      const { matcherForKey } = useMatcherUtils(matchers);

      expect(matcherForKey('type')?.key).toBe('type');
    });

    it('returns undefined for non-existent key', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
      ]);

      const { matcherForKey } = useMatcherUtils(matchers);

      expect(matcherForKey('nonexistent')).toBeUndefined();
    });

    it('returns undefined for undefined key', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
      ]);

      const { matcherForKey } = useMatcherUtils(matchers);

      expect(matcherForKey(undefined)).toBeUndefined();
    });
  });

  describe('matcherForKeyValue', () => {
    it('finds matcher by keyValue', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type', 'typeValue'),
        createStringMatcher('status'),
      ]);

      const { matcherForKeyValue } = useMatcherUtils(matchers);

      expect(matcherForKeyValue('typeValue')?.key).toBe('type');
    });

    it('returns undefined for non-existent keyValue', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
      ]);

      const { matcherForKeyValue } = useMatcherUtils(matchers);

      expect(matcherForKeyValue('nonexistent')).toBeUndefined();
    });
  });
});
