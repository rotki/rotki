import type { ComputedRef } from 'vue';
import type { HighlightType } from '@/modules/history/events/action-types';

interface UseHistoryEventHighlightsReturn {
  highlightedIdentifiers: ComputedRef<string[] | undefined>;
  highlightedGroupIdentifier: ComputedRef<string | undefined>;
  highlightTypes: ComputedRef<Record<string, HighlightType>>;
}

/**
 * The event-level highlight query params, in precedence order: when the same event is
 * referenced by more than one param, the last entry wins the colour. Adding a highlight
 * flavour means adding a row here, nothing else.
 */
const EVENT_HIGHLIGHT_PARAMS = [
  { key: 'highlightedAccountingEvent', type: 'warning' },
  { key: 'highlightedAssetMovement', type: 'warning' },
  { key: 'highlightedNegativeBalanceEvent', type: 'error' },
  { key: 'highlightedPotentialMatch', type: 'success' },
] as const satisfies readonly { key: string; type: HighlightType }[];

/**
 * Derives the event/group highlight targets (and their highlight colours) from the route query.
 * Kept separate from the filter composable so the latter stays focused on pagination/filtering.
 */
export function useHistoryEventHighlights(): UseHistoryEventHighlightsReturn {
  const route = useRoute();

  const highlightedEvents = computed<{ identifier: string; type: HighlightType }[]>(() => {
    const query = get(route).query;
    return EVENT_HIGHLIGHT_PARAMS
      .filter(({ key }) => query[key])
      .map(({ key, type }) => ({ identifier: query[key]!.toString(), type }));
  });

  const highlightedIdentifiers = computed<string[] | undefined>(() => {
    const identifiers = get(highlightedEvents).map(({ identifier }) => identifier);
    return identifiers.length > 0 ? identifiers : undefined;
  });

  const highlightedGroupIdentifier = computed<string | undefined>(() => {
    const { highlightedInternalTxConflict } = get(route).query;
    return highlightedInternalTxConflict ? highlightedInternalTxConflict.toString() : undefined;
  });

  const highlightTypes = computed<Record<string, HighlightType>>(() => {
    const types: Record<string, HighlightType> = {};
    for (const { identifier, type } of get(highlightedEvents))
      types[identifier] = type;

    const groupId = get(highlightedGroupIdentifier);
    if (groupId)
      types[`group:${groupId}`] = 'warning';
    return types;
  });

  return {
    highlightedGroupIdentifier,
    highlightedIdentifiers,
    highlightTypes,
  };
}
