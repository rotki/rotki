import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import {
  HIGHLIGHT_LOADING_START_TIMEOUT,
  HighlightTargetTypes,
  type HistoryEventNavigationRequest,
  useHistoryEventNavigation,
} from '@/modules/history/events/use-history-event-navigation';

const historyEventsName = '/history/events/';

/**
 * Sets up watchers that consume pending navigation requests.
 * Should be called once from HistoryEventsView to handle navigation
 * from any producer (e.g., MatchAssetMovementsPinned, external packages).
 *
 * Supports two input channels:
 * 1. Composable-based: internal components call requestNavigation() directly
 * 2. Route-based: external packages push route with targetGroupIdentifier + highlight query params (e.g., highlightedNegativeBalanceEvent)
 */
export function useHistoryEventNavigationConsumer(
  pagination: ComputedRef<TablePaginationData>,
  requestPayload?: ComputedRef<HistoryEventRequestPayload>,
  groupLoading?: Ref<boolean>,
): void {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const route = useRoute();
  const { getHistoryEventGroupPosition } = useHistoryEventsApi();
  const {
    consumeNavigation,
    pendingNavigation,
    requestNavigation,
    setHighlightTarget,
  } =
    useHistoryEventNavigation();
  const { notifyError } = useNotifications();

  // Watch for route-based navigation from external packages
  watchImmediate(route, ({ query }) => {
    const { targetGroupIdentifier, highlightedAccountingEvent, highlightedNegativeBalanceEvent, asset } = query;
    if (targetGroupIdentifier && highlightedAccountingEvent) {
      setHighlightTarget(HighlightTargetTypes.ACCOUNTING_EVENT, {
        groupIdentifier: targetGroupIdentifier.toString(),
        identifier: Number(highlightedAccountingEvent),
      });
      requestNavigation({
        assetFilter: typeof asset === 'string' ? asset : undefined,
        highlightedAccountingEvent: Number(highlightedAccountingEvent),
        targetGroupIdentifier: targetGroupIdentifier.toString(),
      });
    }

    if (targetGroupIdentifier && highlightedNegativeBalanceEvent) {
      setHighlightTarget(HighlightTargetTypes.NEGATIVE_BALANCE, {
        groupIdentifier: targetGroupIdentifier.toString(),
        identifier: Number(highlightedNegativeBalanceEvent),
      });
      requestNavigation({
        assetFilter: typeof asset === 'string' ? asset : undefined,
        highlightedNegativeBalanceEvent: Number(highlightedNegativeBalanceEvent),
        targetGroupIdentifier: targetGroupIdentifier.toString(),
      });
    }
  });

  /**
   * Clear all highlight query params from the current route.
   */
  async function clearHighlightsFromRoute(): Promise<void> {
    const {
      highlightedAccountingEvent,
      highlightedAssetMovement,
      highlightedInternalTxConflict,
      highlightedNegativeBalanceEvent,
      highlightedPotentialMatch,
      ...remainingQuery
    } = get(route).query;
    if (
      highlightedAccountingEvent ||
      highlightedAssetMovement ||
      highlightedInternalTxConflict ||
      highlightedPotentialMatch ||
      highlightedNegativeBalanceEvent
    ) {
      await router.replace({ query: remainingQuery });
    }
  }

  /**
   * Build highlight query params from a navigation request.
   */
  function buildHighlightQuery(
    request: HistoryEventNavigationRequest,
    page: number,
  ): Record<string, string> {
    const query: Record<string, string> = { page: page.toString() };

    if (request.highlightedAssetMovement)
      query.highlightedAssetMovement = request.highlightedAssetMovement.toString();

    if (request.highlightedAccountingEvent)
      query.highlightedAccountingEvent = request.highlightedAccountingEvent.toString();

    if (request.highlightedPotentialMatch)
      query.highlightedPotentialMatch = request.highlightedPotentialMatch.toString();

    if (request.highlightedNegativeBalanceEvent)
      query.highlightedNegativeBalanceEvent = request.highlightedNegativeBalanceEvent.toString();

    if (request.highlightedInternalTxConflict)
      query.highlightedInternalTxConflict = request.highlightedInternalTxConflict;

    if (request.assetFilter)
      query.asset = request.assetFilter;

    return query;
  }

  /**
   * Resolve the target group's position within the (possibly asset-filtered)
   * view, so the computed page matches the filter applied on arrival.
   */
  async function resolveGroupPosition(request: HistoryEventNavigationRequest): Promise<number> {
    const basePayload = request.preserveFilters && requestPayload ? get(requestPayload) : undefined;
    const filterPayload = request.assetFilter
      ? { ...basePayload, asset: request.assetFilter }
      : basePayload;
    return getHistoryEventGroupPosition(request.targetGroupIdentifier, filterPayload);
  }

  /**
   * Pop the next fallback request, carrying any remaining fallbacks forward.
   * Returns undefined when none are left.
   */
  function selectNextRequest(request: HistoryEventNavigationRequest): HistoryEventNavigationRequest | undefined {
    if (!request.fallbacks?.length)
      return undefined;

    const [next, ...remaining]: HistoryEventNavigationRequest[] = request.fallbacks;
    return { ...next, fallbacks: remaining.length > 0 ? remaining : undefined };
  }

  /**
   * Wait for the pagination system's loading cycle to complete. The loading may
   * not have started yet (fetchDebounce), so wait for it to start first.
   */
  async function waitForFilterLoad(loading: Ref<boolean>): Promise<void> {
    if (!get(loading)) {
      await until(loading).toBe(true, {
        timeout: HIGHLIGHT_LOADING_START_TIMEOUT,
        throwOnTimeout: false,
      });
    }
    if (get(loading)) {
      await until(loading).toBe(false);
    }
  }

  /**
   * Push the highlight route for a resolved position. An asset-filter or
   * preserveFilters navigation changes a real filter, so it waits for the
   * pagination refetch to settle first (otherwise the push races the refetch
   * and the "clear highlights on filter change" watcher wipes the highlight).
   * Returns false when the request became stale while waiting.
   */
  async function pushHighlight(
    request: HistoryEventNavigationRequest,
    activeRequest: HistoryEventNavigationRequest,
    highlightQuery: Record<string, string>,
  ): Promise<boolean> {
    if ((request.preserveFilters || request.assetFilter) && groupLoading) {
      await waitForFilterLoad(groupLoading);

      // Check if this request is still current after waiting
      if (get(pendingNavigation) !== activeRequest)
        return false;

      // Route now has the correct filter/limit values from the pagination system
      await router.push({
        force: true,
        name: historyEventsName,
        query: { ...get(route).query, ...highlightQuery },
      });
      return true;
    }

    const limit = get(pagination).limit;
    await router.push({
      force: true,
      name: historyEventsName,
      query: { limit: limit.toString(), ...highlightQuery },
    });
    return true;
  }

  // Watch for composable-based navigation requests
  watchImmediate(pendingNavigation, async (request) => {
    if (!request)
      return;

    let currentRequest: HistoryEventNavigationRequest | undefined = request;

    try {
      while (currentRequest) {
        const position = await resolveGroupPosition(currentRequest);

        // Check if this request is still current after the await
        if (get(pendingNavigation) !== request)
          return;

        if (position < 0) {
          // Target not in filtered results, try the next fallback
          const next = selectNextRequest(currentRequest);
          if (next) {
            currentRequest = next;
            continue;
          }
          // No fallbacks left, clear highlights
          await clearHighlightsFromRoute();
          break;
        }

        const page = Math.floor(position / get(pagination).limit) + 1;
        const stillCurrent = await pushHighlight(currentRequest, request, buildHighlightQuery(currentRequest, page));
        if (!stillCurrent)
          return;
        break;
      }
    }
    catch (error: unknown) {
      // Only show notification for user-initiated navigation, not filter-change re-navigation
      if (!request.preserveFilters) {
        notifyError(t('asset_movement_matching.dialog.show_in_events'), getErrorMessage(error));
      }
    }
    finally {
      consumeNavigation();
    }
  });
}
