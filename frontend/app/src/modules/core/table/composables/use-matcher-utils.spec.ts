import type { SearchMatcher, StringSuggestionMatcher } from '@/modules/core/table/filtering';
import { get } from '@vueuse/shared';
import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { useMatcherUtils } from '@/modules/core/table/composables/use-matcher-utils';

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
    it('should return all matcher keys', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
        createStringMatcher('status'),
      ]);

      const { validKeys } = useMatcherUtils(matchers);

      expect(get(validKeys)).toEqual(['type', 'status']);
    });

    it('should return empty array for no matchers', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([]);

      const { validKeys } = useMatcherUtils(matchers);

      expect(get(validKeys)).toEqual([]);
    });
  });

  describe('matcherForKey', () => {
    it('should find matcher by key', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
        createStringMatcher('status'),
      ]);

      const { matcherForKey } = useMatcherUtils(matchers);

      expect(matcherForKey('type')?.key).toBe('type');
    });

    it('should return undefined for non-existent key', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
      ]);

      const { matcherForKey } = useMatcherUtils(matchers);

      expect(matcherForKey('nonexistent')).toBeUndefined();
    });

    it('should return undefined for undefined key', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
      ]);

      const { matcherForKey } = useMatcherUtils(matchers);

      expect(matcherForKey(undefined)).toBeUndefined();
    });
  });

  describe('matcherForKeyValue', () => {
    it('should find matcher by keyValue', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type', 'typeValue'),
        createStringMatcher('status'),
      ]);

      const { matcherForKeyValue } = useMatcherUtils(matchers);

      expect(matcherForKeyValue('typeValue')?.key).toBe('type');
    });

    it('should return undefined for non-existent keyValue', () => {
      const matchers = ref<SearchMatcher<any, any>[]>([
        createStringMatcher('type'),
      ]);

      const { matcherForKeyValue } = useMatcherUtils(matchers);

      expect(matcherForKeyValue('nonexistent')).toBeUndefined();
    });
  });
});
