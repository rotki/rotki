import type { ComputedRef, Ref } from 'vue';
import type {
  MatchedKeyword,
  MatchedKeywordWithBehaviour,
  SearchMatcher,
  Suggestion,
} from '@/modules/core/table/filtering';
import type { ChangeSource } from '@/modules/core/table/use-change-intent';
import { isEqual } from 'es-toolkit';
import { matchesFromSelection, selectionFromMatches } from '@/modules/core/table/filter-codec';

type Matcher = SearchMatcher<string, string>;

type MatcherResolver = (key: string | undefined) => Matcher | undefined;

interface UseFilterModelReturn {
  /** The chip selection: the editing model, source of truth for edits. */
  selection: Readonly<Ref<Suggestion[]>>;
  /** The backend `matches` object, derived from the selection. */
  matches: ComputedRef<Partial<MatchedKeyword<string>>>;
  /** Replaces the selection, dropping chips that fail their matcher's validation. */
  setSelection: (pairs: Suggestion[]) => void;
  /** Clears all chips. */
  clearAll: () => void;
  /**
   * Rebuilds the selection from an externally-sourced `matches` object (route restore,
   * saved view, mount). Skips the echo of a change this model itself just produced, so a
   * round-trip does not regroup, reorder, or drop chips: the property PR #12584 fixed with
   * a `lastEmitted` guard, here intrinsic to the model.
   */
  setFromMatches: (matches: MatchedKeywordWithBehaviour<string>, source?: ChangeSource) => void;
}

/**
 * Stage 4 `useFilterModel`, first cut. Owns the filter editing state (the chip
 * `selection`) and derives the wire `matches` from it via the pure codec. The self-echo
 * guard lives here at the single `setFromMatches` choke point.
 *
 * Not yet generic over the matches/matcher types (uses the codec's `<string>` shapes) and
 * not yet wired into `useServerTable`; that carve-out, plus the `FieldDef`/`ActiveFilter`
 * modernization, are later steps. See the Stage 4 design spec.
 */
export function useFilterModel(
  matcherForKey: MatcherResolver,
  matcherForKeyValue: MatcherResolver,
): UseFilterModelReturn {
  const selection = ref<Suggestion[]>([]);

  const matches = computed<Partial<MatchedKeyword<string>>>(
    () => matchesFromSelection(get(selection), matcherForKey).matches,
  );

  function setSelection(pairs: Suggestion[]): void {
    set(selection, matchesFromSelection(pairs, matcherForKey).validSelection);
  }

  function clearAll(): void {
    set(selection, []);
  }

  function setFromMatches(incoming: MatchedKeywordWithBehaviour<string>, source?: ChangeSource): void {
    // The echo of our own emit equals what we already hold; rebuilding from it would
    // regroup/reorder the chips (PR #12584). Only genuine external changes rebuild.
    if (source === 'self' || isEqual(incoming, get(matches)))
      return;

    set(selection, selectionFromMatches(incoming, matcherForKeyValue, get(selection)));
  }

  return {
    clearAll,
    matches,
    selection: shallowReadonly(selection),
    setFromMatches,
    setSelection,
  };
}
