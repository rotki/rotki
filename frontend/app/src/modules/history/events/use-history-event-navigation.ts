import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { startPromise } from '@shared/utils';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';

// Re-exported here (the highlight-navigation module) so consumers that already depend on it can
// pull in the route-derived highlight targets without an extra import dependency.
export { useHistoryEventHighlights } from '@/modules/history/events/use-history-event-highlights';

/**
 * Timing constants coordinating highlight navigation with pagination, derived from one base debounce
 * so they stay in sync. The loading-start timeout is 5x the filter debounce, so the loading state
 * has headroom to become true before we wait for it to finish.
 */
export const HIGHLIGHT_FILTER_DEBOUNCE = 100;

export const HIGHLIGHT_LOADING_START_TIMEOUT = HIGHLIGHT_FILTER_DEBOUNCE * 5;

export interface HistoryEventNavigationRequest {
  /** Group to navigate to (used for getHistoryEventGroupPosition API call) */
  targetGroupIdentifier: string;
  /** Event ID for selected asset movement highlight (warning/yellow) */
  highlightedAssetMovement?: number;
  /** Event ID for accounting overlay divergence highlight (warning/yellow) */
  highlightedAccountingEvent?: number;
  /** Event ID for potential match highlight (success/green) */
  highlightedPotentialMatch?: number;
  /** Event ID for negative balance highlight (error/red) */
  highlightedNegativeBalanceEvent?: number;
  /** Tx hash for internal tx conflict highlight (warning/yellow, group-based) */
  highlightedInternalTxConflict?: string;
  /** Asset identifier to keep as a filter on the events page. The target's page is
   *  computed within this asset-filtered view and the param is preserved in the final
   *  route query, so the highlight and the asset filter coexist. */
  assetFilter?: string;
  /** When true, preserve current route filters and calculate position within filtered view */
  preserveFilters?: boolean;
  /** Fallback requests to try when the target is not found in filtered results */
  fallbacks?: HistoryEventNavigationRequest[];
}

export interface HighlightTarget {
  identifier: number;
  groupIdentifier: string;
}

export const HighlightTargetTypes = {
  ACCOUNTING_EVENT: 'accountingEvent',
  ASSET_MOVEMENT: 'assetMovement',
  INTERNAL_TX_CONFLICT: 'internalTxConflict',
  NEGATIVE_BALANCE: 'negativeBalance',
  POTENTIAL_MATCH: 'potentialMatch',
} as const;

export type HighlightTargetType = (typeof HighlightTargetTypes)[keyof typeof HighlightTargetTypes];

const historyEventsName = '/history/events/';
const pendingNavigation = ref<HistoryEventNavigationRequest>();
const isNavigating = ref<boolean>(false);

const highlightTargets = ref<Partial<Record<HighlightTargetType, HighlightTarget>>>({});

export const useHistoryEventNavigation = createSharedComposable(() => {
  const router = useRouter();
  const route = useRoute();
  const { getHistoryEventGroupPosition } = useHistoryEventsApi();

  function requestNavigation(request: HistoryEventNavigationRequest): void {
    set(isNavigating, true);
    set(pendingNavigation, request);

    /**
     * If not on the history events page, navigate there first.
     * The consumer will pick up the pending request via watchImmediate when it mounts.
     */
    if (get(route).name !== historyEventsName) {
      startPromise(router.push({ name: historyEventsName }));
    }
  }

  function consumeNavigation(): void {
    set(pendingNavigation, undefined);
    set(isNavigating, false);
  }

  function setHighlightTarget(type: HighlightTargetType, target: HighlightTarget): void {
    set(highlightTargets, { ...get(highlightTargets), [type]: target });
  }

  function clearHighlightTarget(type: HighlightTargetType): void {
    const current = { ...get(highlightTargets) };
    delete current[type];
    set(highlightTargets, current);
  }

  function clearAllHighlightTargets(): void {
    set(highlightTargets, {});
  }

  /**
   * Find the page containing the highest-priority highlighted event within the given filters.
   *
   * @remarks
   * `highlightTargets` is the sole source of truth for which candidates to check, and they are tried
   * in priority order: green, then yellow, then red.
   *
   * @returns the 1-based page number, or `-1` when no highlighted event is found
   */
  async function findHighlightPage(
    filterPayload: HistoryEventRequestPayload,
    limit: number,
  ): Promise<number> {
    const targets = get(highlightTargets);

    const candidates: string[] = [
      targets.accountingEvent?.groupIdentifier,
      targets.potentialMatch?.groupIdentifier,
      targets.assetMovement?.groupIdentifier,
      targets.internalTxConflict?.groupIdentifier,
      targets.negativeBalance?.groupIdentifier,
    ].filter((id): id is string => !!id);

    if (candidates.length === 0)
      return -1;

    for (const groupIdentifier of candidates) {
      try {
        const position = await getHistoryEventGroupPosition(groupIdentifier, filterPayload);
        if (position >= 0)
          return Math.floor(position / limit) + 1;
      }
      catch {
        // Position API failed for this candidate, try next
      }
    }

    return -1;
  }

  return {
    clearAllHighlightTargets,
    clearHighlightTarget,
    consumeNavigation,
    findHighlightPage,
    highlightTargets,
    isNavigating,
    pendingNavigation,
    requestNavigation,
    setHighlightTarget,
  };
});
