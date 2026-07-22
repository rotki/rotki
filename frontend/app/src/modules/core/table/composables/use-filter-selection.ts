import type { DeepReadonly, Ref } from 'vue';
import type {
  MatchedKeywordWithBehaviour,
  SearchMatcher,
  Suggestion,
} from '@/modules/core/table/filtering';
import { assert } from '@rotki/common';
import { useFilterModel } from '@/modules/core/table/use-filter-model';

interface SuggestionText {
  text: string;
  startSelection: number;
  endSelection: number;
}

interface UseFilterSelectionReturn {
  selection: Readonly<Ref<Suggestion[]>>;
  suggestionBeingEdited: DeepReadonly<Ref<Suggestion | undefined>>;
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

/**
 * The filter chip UI's edit layer. The state (the chip `selection`), the codec (chip
 * <-> `matches`), and the self-echo guard now live in `useFilterModel`; this composable
 * keeps the presentation-only concerns: the inline search text, the chip being edited,
 * and add/edit-in-place (`applyFilter`). `restoreSelection` delegates to the model's
 * guarded `setFromMatches`, so the round-trip echo no longer regroups or reorders chips
 * (PR #12584), without a bolt-on guard here.
 */
export function useFilterSelection(
  search: Ref<string>,
  matcherForKey: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined,
  matcherForKeyValue: (searchKey: string | undefined) => SearchMatcher<any, any> | undefined,
  emit: (event: 'update:matches', matches: MatchedKeywordWithBehaviour<any>) => void,
): UseFilterSelectionReturn {
  const { matches, selection, setFromMatches, setSelection } = useFilterModel(matcherForKey, matcherForKeyValue);
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

  /** Commits a chip list to the model and emits the derived matches. */
  function updateMatches(pairs: Suggestion[]): void {
    setSelection(pairs);
    emit('update:matches', get(matches));
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

  /** Rebuilds the selection from an external matches, skipping our own echo (see model). */
  function restoreSelection(matchesData: MatchedKeywordWithBehaviour<any>): void {
    setFromMatches(matchesData);
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
    suggestionBeingEdited: readonly(suggestionBeingEdited),
    updateEditSuggestionSearch,
    updateMatches,
  };
}
