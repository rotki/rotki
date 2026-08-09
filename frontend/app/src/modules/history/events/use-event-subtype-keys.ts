import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { Filters } from '@/modules/history/events/use-events-filter';
import { isEqual } from 'es-toolkit';

/**
 * Only `Object.keys` is read off the mapping here, so the shape is kept deliberately loose to accept
 * whatever the event-type schema currently produces.
 */
type GlobalMapping = Record<string, Record<string, unknown>>;

interface UseEventSubtypeKeysOptions {
  /** The filter state. Stale subtype selections are pruned from it as the valid set narrows. */
  modelFilters: Ref<Filters>;
  /** Event type to subtype mapping, as served by the backend's event-type schema. */
  globalMapping: MaybeRefOrGetter<GlobalMapping>;
  /** When true the subtype filter is not offered at all, so no keys are derived. */
  disabled: MaybeRefOrGetter<boolean | undefined>;
}

function asArray(value: Filters[keyof Filters]): string[] {
  if (value === undefined)
    return [];

  return Array.isArray(value) ? value.map(entry => entry.toString()) : [value.toString()];
}

/**
 * The event subtypes that are selectable given the currently selected event types: the union of the
 * subtypes each selected type allows, or every known subtype when no type is selected.
 *
 * Also prunes the filter state: when the valid set narrows, subtypes that are no longer offered are
 * dropped from the selection so the filter cannot keep querying a subtype the UI no longer shows.
 */
export function useEventSubtypeKeys(
  { disabled, globalMapping, modelFilters }: UseEventSubtypeKeysOptions,
): ComputedRef<string[]> {
  const validSubtypeKeys = computed<string[]>(() => {
    if (toValue(disabled))
      return [];

    const mapping = toValue(globalMapping);
    if (Object.keys(mapping).length === 0)
      return [];

    const selectedEventTypes = asArray(get(modelFilters)?.eventTypes);
    if (selectedEventTypes.length === 0)
      return Object.values(mapping).flatMap(entry => Object.keys(entry));

    return selectedEventTypes.flatMap(selected => Object.keys(mapping[selected] ?? {}));
  });

  watch(validSubtypeKeys, (keys) => {
    if (keys.length === 0)
      return;

    const selectedEventSubtypes = asArray(get(modelFilters)?.eventSubtypes);
    if (selectedEventSubtypes.length === 0)
      return;

    const filtered = selectedEventSubtypes.filter(item => keys.includes(item));
    if (isEqual(filtered, selectedEventSubtypes))
      return;

    set(modelFilters, {
      ...get(modelFilters),
      eventSubtypes: filtered.length > 0 ? filtered : undefined,
    });
  });

  return validSubtypeKeys;
}
