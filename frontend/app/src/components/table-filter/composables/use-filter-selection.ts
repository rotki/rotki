import type { Ref } from 'vue';
import type {
  MatchedKeyword,
  MatchedKeywordWithBehaviour,
  SearchMatcher,
  Suggestion,
} from '@/types/filtering';
import { assert } from '@rotki/common';
import { arrayify } from '@/utils/array';

interface SuggestionText {
  text: string;
  startSelection: number;
  endSelection: number;
}

interface UseFilterSelectionReturn {
  selection: Ref<Suggestion[]>;
  suggestionBeingEdited: Ref<Suggestion | undefined>;
  updateMatches: (pairs: Suggestion[]) => void;
  restoreSelection: (matchesData: MatchedKeywordWithBehaviour<any>) => void;
  isSuggestionBeingEdited: (suggestion: Suggestion) => boolean;
  clickItem: (item: Suggestion) => void;
  cancelEditSuggestion: (skipClearSearch?: boolean) => void;
  updateEditSuggestionSearch: (value: string) => void;
  getSuggestionText: (suggestion: Suggestion) => SuggestionText;
  getDisplayValue: (suggestion: Suggestion) => string;
  applyFilter: (filter: Suggestion) => void;
}

export function useFilterSelection(
  search: Ref<string>,
  matcherForKey: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined,
  matcherForKeyValue: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined,
  emit: (event: 'update:matches', matches: MatchedKeywordWithBehaviour<any>) => void,
): UseFilterSelectionReturn {
  const selection = ref<Suggestion[]>([]);
  const suggestionBeingEdited = ref<Suggestion>();

  // TODO: This is too specific for custom asset, move it!
  function getDisplayValue(suggestion: Suggestion): string {
    const value = suggestion.value;
    if (typeof value === 'string')
      return value;

    return value.isCustomAsset ? value.name : value.symbol;
  }

  function getSuggestionText(suggestion: Suggestion): SuggestionText {
    const operator = suggestion.exclude ? '!=' : '=';
    const startSelection = suggestion.key.length + operator.length;
    const value = getDisplayValue(suggestion);
    return {
      endSelection: startSelection + value.length,
      startSelection,
      text: `${suggestion.key}${operator}${value}`,
    };
  }

  function isSuggestionBeingEdited(suggestion: Suggestion): boolean {
    const edited = get(suggestionBeingEdited);
    if (!edited)
      return false;

    return getSuggestionText(suggestion).text === getSuggestionText(edited).text;
  }

  function clickItem(item: Suggestion): void {
    if (typeof item.value !== 'boolean') {
      set(suggestionBeingEdited, item);
      set(search, `${item.key}${item.exclude ? '!=' : '='}`);
    }
  }

  function cancelEditSuggestion(skipClearSearch = false): void {
    set(suggestionBeingEdited, undefined);
    if (!skipClearSearch) {
      set(search, '');
    }
  }

  function updateEditSuggestionSearch(value: string): void {
    const beingEdited = get(suggestionBeingEdited);
    if (!beingEdited)
      return;

    set(search, `${beingEdited.key}${beingEdited.exclude ? '!=' : '='}${value}`);
  }

  function updateMatches(pairs: Suggestion[]): void {
    const matched: Partial<MatchedKeyword<any>> = {};
    const validPairs: Suggestion[] = [];

    for (const entry of pairs) {
      const key = entry.key;
      const matcher = matcherForKey(key);
      if (!matcher)
        continue;

      const valueKey = (matcher.keyValue || matcher.key) as string;
      let transformedKeyword: string | boolean = '';

      if ('string' in matcher) {
        if (typeof entry.value !== 'string')
          continue;

        if (matcher.validate(entry.value)) {
          transformedKeyword = matcher.serializer?.(entry.value) || entry.value;

          if (entry.exclude)
            transformedKeyword = `!${transformedKeyword}`;
        }
        else {
          continue;
        }
      }
      else if ('asset' in matcher) {
        transformedKeyword = typeof entry.value !== 'string' ? entry.value.identifier : entry.value;
      }
      else {
        transformedKeyword = true;
      }

      if (!transformedKeyword)
        continue;

      validPairs.push(entry);

      if (matcher.multiple) {
        if (!matched[valueKey])
          matched[valueKey] = [];

        (matched[valueKey] as (string | boolean)[]).push(transformedKeyword);
      }
      else {
        matched[valueKey] = transformedKeyword;
      }
    }

    set(selection, validPairs);
    emit('update:matches', matched);
  }

  function findBeingSelectedIndex(selectionList: Suggestion[]): number {
    return selectionList.findIndex(sel => isSuggestionBeingEdited(sel));
  }

  function applyFilter(filter: Suggestion): void {
    let newSelection = [...get(selection)];
    const key = filter.key;
    const index = newSelection.findIndex(value => value.key === key);
    const matcher = matcherForKey(key);
    assert(matcher);

    if (index >= 0 && (!matcher.multiple || newSelection[index].exclude !== filter.exclude))
      newSelection = newSelection.filter(item => item.key !== key);

    let beingEditedIndex = -1;

    const beingEdited = get(suggestionBeingEdited);
    if (beingEdited) {
      beingEditedIndex = findBeingSelectedIndex(newSelection);
      if (beingEditedIndex > -1) {
        newSelection.splice(beingEditedIndex, 1);
      }
      set(suggestionBeingEdited, undefined);
    }

    if (beingEditedIndex === -1) {
      newSelection.push(filter);
    }
    else {
      newSelection.splice(beingEditedIndex, 0, filter);
    }

    updateMatches(newSelection);
    set(search, '');
  }

  function restoreSelection(matchesData: MatchedKeywordWithBehaviour<any>): void {
    const oldSelection = get(selection);
    const newSelection: Suggestion[] = [];
    Object.entries(matchesData).forEach(([key, value]) => {
      const foundMatchers = matcherForKeyValue(key);

      if (!(foundMatchers && value))
        return;

      const values = arrayify(value);
      const asset = 'asset' in foundMatchers;
      const boolean = 'boolean' in foundMatchers;

      values.forEach((val) => {
        let deserializedValue = null;
        if (asset) {
          const prevAssetSelection = oldSelection.find(({ key }) => key === foundMatchers.key);
          if (prevAssetSelection)
            deserializedValue = prevAssetSelection.value;
        }

        let exclude = false;
        if (!deserializedValue) {
          if (boolean || typeof val === 'boolean') {
            deserializedValue = true;
          }
          else if (typeof val === 'string') {
            let normalizedValue = val;
            if (!asset && val.startsWith('!')) {
              normalizedValue = val.substring(1);
              exclude = true;
            }
            deserializedValue = foundMatchers.deserializer?.(normalizedValue) || normalizedValue;
          }
        }

        if (deserializedValue === null)
          return;

        newSelection.push({
          asset,
          exclude,
          index: 0,
          key: foundMatchers.key,
          total: 1,
          value: deserializedValue,
        });
      });
    });

    set(selection, newSelection);
  }

  return {
    applyFilter,
    cancelEditSuggestion,
    clickItem,
    getDisplayValue,
    getSuggestionText,
    isSuggestionBeingEdited,
    restoreSelection,
    selection,
    suggestionBeingEdited,
    updateEditSuggestionSearch,
    updateMatches,
  };
}
