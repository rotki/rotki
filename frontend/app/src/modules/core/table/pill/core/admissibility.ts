import type { FieldDef, FilterState } from '@/modules/core/table/pill/core/types';

/** Every active filter's values, keyed by field, as a field's `admits` reads them. */
function valuesByField(state: FilterState): Record<string, readonly string[]> {
  return Object.fromEntries(state.map(filter => [filter.fieldKey, filter.values]));
}

/**
 * Drops the values a field no longer admits, given what the other fields hold.
 *
 * The other half of `FieldDef.admits`: narrowing an option list only governs what can be *added*,
 * so without this a value picked before the narrowing stays in the filter and keeps being sent. A
 * filter left with no values at all is removed, since an empty pill filters nothing.
 *
 * Returns the state unchanged, by reference, when nothing was inadmissible. Callers set this
 * straight back onto a ref, so preserving identity is what keeps a no-op from being an update.
 */
export function pruneInadmissible(state: FilterState, fields: readonly FieldDef[]): FilterState {
  if (!fields.some(field => field.admits))
    return state;

  const values = valuesByField(state);
  let changed = false;

  const pruned = state.flatMap((filter) => {
    const admits = fields.find(field => field.key === filter.fieldKey)?.admits;
    if (!admits || filter.values.length === 0)
      return [filter];

    const allowed = admits(values);
    // An empty list is "not known yet", not "nothing is allowed": the option lists are store-backed
    // and a mapping that has not loaded must not wipe what the user picked.
    if (allowed.length === 0)
      return [filter];

    const kept = filter.values.filter(value => allowed.includes(value));
    if (kept.length === filter.values.length)
      return [filter];

    changed = true;
    return kept.length > 0 ? [{ ...filter, values: kept }] : [];
  });

  return changed ? pruned : state;
}
