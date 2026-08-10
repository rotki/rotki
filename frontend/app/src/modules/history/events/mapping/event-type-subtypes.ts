import { uniqueStrings } from '@/modules/core/common/data/data';

/**
 * Only `Object.keys` is read off the mapping here, so the shape is kept deliberately loose to accept
 * whatever the event-type schema currently produces.
 */
export type EventTypeSubtypeMapping = Record<string, Record<string, unknown>>;

/**
 * The subtypes a set of event types admits, deduplicated; every known subtype when no type is
 * given, and none at all while the mapping is still empty.
 *
 * The backend reads event types and subtypes as a cross product, so a subtype no selected type
 * admits matches nothing and the table goes silently empty. Both tables that filter on the pair
 * (history events, accounting rules) narrow their option list with this and declare it as what the
 * subtype field `admits`, so the two halves of the rule come from one lookup.
 */
export function subtypesForTypes(
  mapping: EventTypeSubtypeMapping,
  eventTypes: readonly string[],
): string[] {
  if (Object.keys(mapping).length === 0)
    return [];

  const keys = eventTypes.length === 0
    ? Object.values(mapping).flatMap(entry => Object.keys(entry))
    : eventTypes.flatMap(selected => Object.keys(mapping[selected] ?? {}));

  return keys.filter(uniqueStrings);
}
