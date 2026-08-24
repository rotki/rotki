import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { MatchedKeyword, MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import type { ActiveFilter, FieldDef, FilterState } from '@/modules/core/table/pill/core/types';
import type { ChangeSource } from '@/modules/core/table/use-change-intent';
import { isEqual } from 'es-toolkit';
import { pruneInadmissible } from '@/modules/core/table/pill/core/admissibility';
import { matchesFromState, stateFromMatches } from '@/modules/core/table/pill/core/codec';

export interface UseFilterStateReturn {
  /** The active filters: the editing model, source of truth for edits. */
  state: Readonly<Ref<FilterState>>;
  /** Matcher-bound wire object, derived from the state (same shape as `TableFilter`). */
  matches: ComputedRef<Partial<MatchedKeyword<string>>>;
  /** Param-bound values (external filters), derived from the state, keyed by param key. */
  params: ComputedRef<Record<string, string | string[] | boolean>>;
  /** Adds a filter, replacing any existing one for the same field (one filter per field). */
  addFilter: (filter: ActiveFilter) => void;
  /** Patches the filter for a field; a no-op when the field has no active filter. */
  updateFilter: (fieldKey: string, patch: Partial<Omit<ActiveFilter, 'fieldKey'>>) => void;
  /** Removes the filter for a field. */
  removeFilter: (fieldKey: string) => void;
  /** Clears all filters. */
  clearAll: () => void;
  /**
   * Rebuilds the state from an externally-sourced wire form (route restore, saved view,
   * mount). Skips the echo of a change this model itself just produced so a round-trip does
   * not reorder or drop filters — the same self-echo property `useFilterModel` carries for
   * the old bar (PR #12584), here over `ActiveFilter[]`.
   */
  setFromMatches: (
    matches: MatchedKeywordWithBehaviour<string>,
    params: Record<string, unknown>,
    source?: ChangeSource,
  ) => void;
}

/**
 * The pill bar's Layer-2 state container (the plan's `use-filter-state`, the `ActiveFilter[]`
 * evolution of `useFilterModel`). Owns `state: ActiveFilter[]` and derives the transported
 * `matches` + `params` through the pure codec over the given `fields`. No DOM, no async: asset
 * search is the editor's concern, injected there, not called in a setter (Pinia sync-only rule).
 *
 * Not yet wired into any bar. The old Suggestion-based `useFilterModel`/`useFilterSelection`
 * stay as they are; unifying the two happens with the pill components (Phase 2), where the
 * asset-display translation is verified in-app.
 */
export function useFilterState(fields: MaybeRefOrGetter<FieldDef[]>): UseFilterStateReturn {
  const state = ref<FilterState>([]);

  const serialized = computed(() => matchesFromState(get(state), toValue(fields)));
  const matches = computed<Partial<MatchedKeyword<string>>>(() => get(serialized).matches);
  const params = computed<Record<string, string | string[] | boolean>>(() => get(serialized).params);

  /**
   * The one way state is written. Every entry point goes through here so a field's `admits` is
   * applied to all of them alike — an edit, a removal, and the route/saved-view restore below.
   */
  function commit(next: FilterState): void {
    const pruned = pruneInadmissible(next, toValue(fields));
    // A rebuild that changes nothing must not change identity. `matches`/`params` are derived from
    // this ref, and the bar writes them back on every identity change, so an equal-but-new array is
    // an update that produces another update. That is survivable while the two sides converge, but
    // they cannot converge when a field is removed while its filter is still active: the codec
    // skips a filter whose field is gone, so the derived bag permanently disagrees with the
    // incoming one, `setFromMatches` rebuilds on every flush, and the bar recurses until Vue aborts
    // the render. Comparing by value is what makes a no-op rebuild a no-op.
    if (isEqual(pruned, get(state)))
      return;

    set(state, pruned);
  }

  function addFilter(filter: ActiveFilter): void {
    commit([...get(state).filter(item => item.fieldKey !== filter.fieldKey), filter]);
  }

  function updateFilter(fieldKey: string, patch: Partial<Omit<ActiveFilter, 'fieldKey'>>): void {
    commit(get(state).map(item => (item.fieldKey === fieldKey ? { ...item, ...patch } : item)));
  }

  function removeFilter(fieldKey: string): void {
    commit(get(state).filter(item => item.fieldKey !== fieldKey));
  }

  function clearAll(): void {
    set(state, []);
  }

  /**
   * What the declaring fields currently admit. Reading it *calls* `admits`, so whatever those
   * lookups depend on — a store-backed mapping, another field's values — is tracked here.
   * Watching the field list instead would miss a mapping that loads without rebuilding the list.
   */
  const admitted = computed<string[][]>(() => {
    const values = Object.fromEntries(get(state).map(filter => [filter.fieldKey, filter.values]));
    return toValue(fields).filter(field => field.admits).map(field => [...field.admits!(values)]);
  });

  /**
   * The option lists behind `admits` are store-backed, so one can arrive after the state it governs:
   * a link restored before the event-type mapping loads keeps its value (see `pruneInadmissible`)
   * and has to be pruned once the mapping answers. Re-pruning cannot loop, because a second pass
   * over an already-pruned state returns it by reference and `set` is then a no-op.
   */
  watch(admitted, () => {
    commit(get(state));
  });

  function setFromMatches(
    incoming: MatchedKeywordWithBehaviour<string>,
    incomingParams: Record<string, unknown>,
    source?: ChangeSource,
  ): void {
    if (source === 'self' || (isEqual(incoming, get(matches)) && isEqual(incomingParams, get(params))))
      return;

    commit(stateFromMatches(incoming, incomingParams, toValue(fields)));
  }

  return {
    addFilter,
    clearAll,
    matches,
    params,
    removeFilter,
    setFromMatches,
    state: shallowReadonly(state),
    updateFilter,
  };
}
