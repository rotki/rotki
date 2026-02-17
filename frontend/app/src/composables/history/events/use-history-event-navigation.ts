import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { startPromise } from '@shared/utils';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { Routes } from '@/router/routes';

/**
 * Timing constants that coordinate highlight navigation with the pagination system.
 * All values are derived from a single base debounce so they stay in sync.
 *
 * - Filter watcher fires first so setPage() can reset the fetch timer (single fetch).
 * - Fetch debounce is 2x the filter debounce.
 * - Loading-start timeout is 5x the filter debounce, giving the loading state
 *   enough headroom to become true before we wait for it to finish.
 */
export const HIGHLIGHT_FILTER_DEBOUNCE = 100;

export const HIGHLIGHT_FETCH_DEBOUNCE = HIGHLIGHT_FILTER_DEBOUNCE * 2;

export const HIGHLIGHT_LOADING_START_TIMEOUT = HIGHLIGHT_FILTER_DEBOUNCE * 5;

export interface HistoryEventNavigationRequest {
  /** Group to navigate to (used for getHistoryEventGroupPosition API call) */
  targetGroupIdentifier: string;
  /** Event ID for selected asset movement highlight (warning/yellow) */
  highlightedAssetMovement?: number;
  /** Event ID for potential match highlight (success/green) */
  highlightedPotentialMatch?: number;
  /** Event ID for negative balance highlight (error/red) */
  highlightedNegativeBalanceEvent?: number;
  /** When true, preserve current route filters and calculate position within filtered view */
  preserveFilters?: boolean;
  /** Fallback requests to try when the target is not found in filtered results */
  fallbacks?: HistoryEventNavigationRequest[];
}

export interface HighlightTarget {
  identifier: number;
  groupIdentifier: string;
}

export type HighlightTargetType = 'assetMovement' | 'negativeBalance' | 'potentialMatch';

const historyEventsPath = Routes.HISTORY_EVENTS.toString();
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
    if (!get(route).path.startsWith(historyEventsPath)) {
      startPromise(router.push({ path: historyEventsPath }));
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
   * Uses highlightTargets as the sole source of truth for which candidates to check.
   * Tries candidates in priority order (green > yellow > red).
   * Returns the 1-based page number, or -1 if no highlighted event is found.
   */
  async function findHighlightPage(
    filterPayload: HistoryEventRequestPayload,
    limit: number,
  ): Promise<number> {
    const targets = get(highlightTargets);

    const candidates: string[] = [
      targets.potentialMatch?.groupIdentifier,
      targets.assetMovement?.groupIdentifier,
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
