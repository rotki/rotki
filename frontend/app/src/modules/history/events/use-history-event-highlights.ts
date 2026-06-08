import type { ComputedRef } from 'vue';
import type { HighlightType } from '@/modules/history/events/action-types';

interface UseHistoryEventHighlightsReturn {
  highlightedIdentifiers: ComputedRef<string[] | undefined>;
  highlightedGroupIdentifier: ComputedRef<string | undefined>;
  highlightTypes: ComputedRef<Record<string, HighlightType>>;
}

/**
 * Derives the event/group highlight targets (and their highlight colours) from the route query.
 * Kept separate from the filter composable so the latter stays focused on pagination/filtering.
 */
export function useHistoryEventHighlights(): UseHistoryEventHighlightsReturn {
  const route = useRoute();

  const highlightedIdentifiers = computed<string[] | undefined>(() => {
    const { highlightedAssetMovement, highlightedPotentialMatch, highlightedNegativeBalanceEvent } = get(route).query;
    const identifiers: string[] = [];
    if (highlightedAssetMovement)
      identifiers.push(highlightedAssetMovement.toString());
    if (highlightedPotentialMatch)
      identifiers.push(highlightedPotentialMatch.toString());
    if (highlightedNegativeBalanceEvent)
      identifiers.push(highlightedNegativeBalanceEvent.toString());
    return identifiers.length > 0 ? identifiers : undefined;
  });

  const highlightedGroupIdentifier = computed<string | undefined>(() => {
    const { highlightedInternalTxConflict } = get(route).query;
    return highlightedInternalTxConflict ? highlightedInternalTxConflict.toString() : undefined;
  });

  const highlightTypes = computed<Record<string, HighlightType>>(() => {
    const { highlightedAssetMovement, highlightedPotentialMatch, highlightedNegativeBalanceEvent } = get(route).query;
    const types: Record<string, HighlightType> = {};
    if (highlightedAssetMovement)
      types[highlightedAssetMovement.toString()] = 'warning';
    if (highlightedNegativeBalanceEvent)
      types[highlightedNegativeBalanceEvent.toString()] = 'error';
    if (highlightedPotentialMatch)
      types[highlightedPotentialMatch.toString()] = 'success';
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
