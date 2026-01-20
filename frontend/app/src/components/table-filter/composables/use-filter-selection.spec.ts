import type { MatchedKeywordWithBehaviour, SearchMatcher, StringSuggestionMatcher, Suggestion } from '@/types/filtering';
import { get, set } from '@vueuse/shared';
import { describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import { useFilterSelection } from '@/components/table-filter/composables/use-filter-selection';

describe('composables/use-filter-selection', () => {
  function createStringMatcher(key: string, keyValue?: string, multiple = true): StringSuggestionMatcher<string, string> {
    return {
      description: `filter by ${key}`,
      key,
      keyValue: keyValue ?? key,
      multiple,
      string: true,
      suggestions: () => [`${key} 1`, `${key} 2`],
      validate: () => true,
    };
  }

  function createSuggestion(key: string, value: string, exclude = false): Suggestion {
    return {
      asset: false,
      exclude,
      index: 0,
      key,
      total: 1,
      value,
    };
  }

  type EmitFn = (event: 'update:matches', matches: MatchedKeywordWithBehaviour<any>) => void;

  interface TestSetup {
    search: Ref<string>;
    emit: EmitFn;
    matcherForKey: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined;
    matcherForKeyValue: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined;
  }

  function createTestSetup(matchersList: SearchMatcher<any, any>[] = []): TestSetup {
    const matchers = ref<SearchMatcher<any, any>[]>(matchersList);
    const search = ref<string>('');
    const emit = vi.fn<EmitFn>();

    const matcherForKey = (searchKey: string | undefined): SearchMatcher<any, any> | undefined =>
      get(matchers).find((matcher: SearchMatcher<any, any>) => matcher.key === searchKey);

    const matcherForKeyValue = (searchKey: string | undefined): SearchMatcher<any, any> | undefined =>
      get(matchers).find((matcher: SearchMatcher<any, any>) => matcher.keyValue === searchKey);

    return {
      emit,
      matcherForKey,
      matcherForKeyValue,
      search,
    };
  }

  describe('getDisplayValue', () => {
    it('returns string value directly', () => {
      const setup = createTestSetup();
      const { getDisplayValue } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'test value');
      expect(getDisplayValue(suggestion)).toBe('test value');
    });
  });

  describe('getSuggestionText', () => {
    it('formats suggestion with equals operator', () => {
      const setup = createTestSetup();
      const { getSuggestionText } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value');
      const result = getSuggestionText(suggestion);

      expect(result.text).toBe('type=value');
      expect(result.startSelection).toBe(5);
      expect(result.endSelection).toBe(10);
    });

    it('formats suggestion with not-equals operator when excluded', () => {
      const setup = createTestSetup();
      const { getSuggestionText } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value', true);
      const result = getSuggestionText(suggestion);

      expect(result.text).toBe('type!=value');
      expect(result.startSelection).toBe(6);
      expect(result.endSelection).toBe(11);
    });
  });

  describe('isSuggestionBeingEdited', () => {
    it('returns false when no suggestion is being edited', () => {
      const setup = createTestSetup();
      const { isSuggestionBeingEdited } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value');
      expect(isSuggestionBeingEdited(suggestion)).toBe(false);
    });

    it('returns true when the same suggestion is being edited', () => {
      const setup = createTestSetup();
      const { isSuggestionBeingEdited, clickItem } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value');
      clickItem(suggestion);

      expect(isSuggestionBeingEdited(suggestion)).toBe(true);
    });
  });

  describe('clickItem', () => {
    it('sets suggestionBeingEdited and search for string values', () => {
      const setup = createTestSetup();
      const { suggestionBeingEdited, clickItem } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value');
      clickItem(suggestion);

      expect(get(suggestionBeingEdited)).toStrictEqual(suggestion);
      expect(get(setup.search)).toBe('type=');
    });

    it('sets search with != for excluded items', () => {
      const setup = createTestSetup();
      const { clickItem } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value', true);
      clickItem(suggestion);

      expect(get(setup.search)).toBe('type!=');
    });

    it('does not set editing state for boolean values', () => {
      const setup = createTestSetup();
      const { suggestionBeingEdited, clickItem } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion: Suggestion = {
        asset: false,
        index: 0,
        key: 'active',
        total: 1,
        value: true,
      };
      clickItem(suggestion);

      expect(get(suggestionBeingEdited)).toBeUndefined();
    });
  });

  describe('cancelEditSuggestion', () => {
    it('clears suggestionBeingEdited and search', () => {
      const setup = createTestSetup();
      const { suggestionBeingEdited, clickItem, cancelEditSuggestion } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value');
      clickItem(suggestion);
      cancelEditSuggestion();

      expect(get(suggestionBeingEdited)).toBeUndefined();
      expect(get(setup.search)).toBe('');
    });

    it('preserves search when skipClearSearch is true', () => {
      const setup = createTestSetup();
      const { clickItem, cancelEditSuggestion } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value');
      clickItem(suggestion);
      cancelEditSuggestion(true);

      expect(get(setup.search)).toBe('type=');
    });
  });

  describe('updateEditSuggestionSearch', () => {
    it('updates search with edited value', () => {
      const setup = createTestSetup();
      const { clickItem, updateEditSuggestionSearch } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value');
      clickItem(suggestion);
      updateEditSuggestionSearch('new value');

      expect(get(setup.search)).toBe('type=new value');
    });

    it('does nothing when not editing', () => {
      const setup = createTestSetup();
      const { updateEditSuggestionSearch } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      updateEditSuggestionSearch('new value');

      expect(get(setup.search)).toBe('');
    });
  });

  describe('updateMatches', () => {
    it('emits update:matches with transformed values', () => {
      const setup = createTestSetup([createStringMatcher('type')]);
      const { updateMatches } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value1');
      updateMatches([suggestion]);

      expect(setup.emit).toHaveBeenCalledWith('update:matches', { type: ['value1'] });
    });

    it('handles excluded values with ! prefix', () => {
      const setup = createTestSetup([createStringMatcher('type')]);
      const { updateMatches } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const suggestion = createSuggestion('type', 'value1', true);
      updateMatches([suggestion]);

      expect(setup.emit).toHaveBeenCalledWith('update:matches', { type: ['!value1'] });
    });

    it('filters out invalid suggestions', () => {
      const setup = createTestSetup([createStringMatcher('type')]);
      const { updateMatches } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const validSuggestion = createSuggestion('type', 'value1');
      const invalidSuggestion = createSuggestion('nonexistent', 'value2');
      updateMatches([validSuggestion, invalidSuggestion]);

      expect(setup.emit).toHaveBeenCalledWith('update:matches', { type: ['value1'] });
    });
  });

  describe('applyFilter', () => {
    it('adds new filter to selection', () => {
      const setup = createTestSetup([createStringMatcher('type')]);
      const { applyFilter, selection } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const filter = createSuggestion('type', 'value1');
      applyFilter(filter);

      expect(get(selection)).toHaveLength(1);
      expect(get(selection)[0]).toStrictEqual(filter);
    });

    it('replaces non-multiple matcher values', () => {
      const setup = createTestSetup([createStringMatcher('single', 'single', false)]);
      const { applyFilter, selection } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const filter1 = createSuggestion('single', 'value1');
      const filter2 = createSuggestion('single', 'value2');

      applyFilter(filter1);
      applyFilter(filter2);

      expect(get(selection)).toHaveLength(1);
      expect(get(selection)[0].value).toBe('value2');
    });

    it('clears search after applying', () => {
      const setup = createTestSetup([createStringMatcher('type')]);
      set(setup.search, 'type=value');

      const { applyFilter } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      const filter = createSuggestion('type', 'value');
      applyFilter(filter);

      expect(get(setup.search)).toBe('');
    });
  });

  describe('restoreSelection', () => {
    it('restores selection from matches object', () => {
      const setup = createTestSetup([createStringMatcher('type')]);
      const { restoreSelection, selection } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      restoreSelection({ type: ['value1', 'value2'] });

      expect(get(selection)).toHaveLength(2);
      expect(get(selection)[0].value).toBe('value1');
      expect(get(selection)[1].value).toBe('value2');
    });

    it('restores excluded values with ! prefix', () => {
      const setup = createTestSetup([createStringMatcher('type')]);
      const { restoreSelection, selection } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      restoreSelection({ type: ['!value1'] });

      expect(get(selection)).toHaveLength(1);
      expect(get(selection)[0].value).toBe('value1');
      expect(get(selection)[0].exclude).toBe(true);
    });

    it('handles single values', () => {
      const setup = createTestSetup([createStringMatcher('single', 'single', false)]);
      const { restoreSelection, selection } = useFilterSelection(
        setup.search,
        setup.matcherForKey,
        setup.matcherForKeyValue,
        setup.emit,
      );

      restoreSelection({ single: 'value' });

      expect(get(selection)).toHaveLength(1);
      expect(get(selection)[0].value).toBe('value');
    });
  });
});
