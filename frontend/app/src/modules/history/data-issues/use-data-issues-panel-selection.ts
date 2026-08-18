import type { ComputedRef } from 'vue';
import type { RouteLocationRaw } from 'vue-router';
import type { PanelRow } from '@/modules/history/data-issues/use-data-issues-panel-list';
import { HighlightTargetTypes, useHistoryEventNavigation } from '@/modules/history/events/use-history-event-navigation';

interface UseDataIssuesPanelSelectionReturn {
  activeEventIdentifier: ComputedRef<number | undefined>;
  hasActiveSelection: ComputedRef<boolean>;
  isActiveRow: (row: PanelRow) => boolean;
  goToEvent: (target: RouteLocationRaw) => Promise<void>;
  clearSelection: () => Promise<void>;
}

/**
 * Which card is shown as the "source" of the currently highlighted history event.
 *
 * The route query is the single source of truth for the highlight, so the card
 * mirrors it rather than holding its own selection state. That keeps it in sync
 * automatically when the highlight is cleared from the events view: the card
 * simply stops matching.
 */
export function useDataIssuesPanelSelection(): UseDataIssuesPanelSelectionReturn {
  const router = useRouter();
  const route = useRoute();
  const { clearHighlightTarget } = useHistoryEventNavigation();

  const activeEventIdentifier = computed<number | undefined>(() => {
    const raw = get(route).query.highlightedNegativeBalanceEvent;
    const value = Number(Array.isArray(raw) ? raw[0] : raw);
    return Number.isInteger(value) && value > 0 ? value : undefined;
  });

  const hasActiveSelection = computed<boolean>(() => get(activeEventIdentifier) !== undefined);

  function isActiveRow(row: PanelRow): boolean {
    const identifier = row.description.eventIdentifier;
    return identifier !== undefined && identifier === get(activeEventIdentifier);
  }

  async function goToEvent(target: RouteLocationRaw): Promise<void> {
    await router.push(target);
  }

  /**
   * Clears the selection: strips the highlight query params (which un-highlights both
   * the history row and the source card) and drops the paging target so a later filter
   * change does not re-navigate to the stale event. Mirrors clearHighlight() in the
   * movement matching pinned panel.
   */
  async function clearSelection(): Promise<void> {
    clearHighlightTarget(HighlightTargetTypes.NEGATIVE_BALANCE);
    const { highlightedNegativeBalanceEvent, targetGroupIdentifier, ...remainingQuery } = get(route).query;
    if (highlightedNegativeBalanceEvent || targetGroupIdentifier)
      await router.replace({ query: remainingQuery });
  }

  return {
    activeEventIdentifier,
    clearSelection,
    goToEvent,
    hasActiveSelection,
    isActiveRow,
  };
}
