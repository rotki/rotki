import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { HIGHLIGHT_LOADING_START_TIMEOUT, type HistoryEventNavigationRequest, useHistoryEventNavigation } from '@/composables/history/events/use-history-event-navigation';
import { Routes } from '@/router/routes';
import { useNotificationsStore } from '@/store/notifications';

const historyEventsPath = Routes.HISTORY_EVENTS.toString();

/**
 * Sets up watchers that consume pending navigation requests.
 * Should be called once from HistoryEventsView to handle navigation
 * from any producer (e.g., MatchAssetMovementsPinned, NegativeBalancesDialog, external packages).
 *
 * Supports two input channels:
 * 1. Composable-based: internal components call requestNavigation() directly
 * 2. Route-based: external packages push route with targetGroupIdentifier + highlight query params (e.g., highlightedNegativeBalanceEvent)
 */
export function useHistoryEventNavigationConsumer(
  pagination: ComputedRef<TablePaginationData>,
  pageParams?: ComputedRef<HistoryEventRequestPayload>,
  groupLoading?: Ref<boolean>,
): void {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const route = useRoute();
  const { getHistoryEventGroupPosition } = useHistoryEventsApi();
  const { consumeNavigation, pendingNavigation, requestNavigation, setHighlightTarget } = useHistoryEventNavigation();
  const { notify } = useNotificationsStore();

  // Watch for route-based navigation from external packages
  watchImmediate(route, ({ query }) => {
    const { targetGroupIdentifier, highlightedNegativeBalanceEvent } = query;
    if (targetGroupIdentifier && highlightedNegativeBalanceEvent) {
      setHighlightTarget('negativeBalance', {
        groupIdentifier: targetGroupIdentifier.toString(),
        identifier: Number(highlightedNegativeBalanceEvent),
      });
      requestNavigation({
        highlightedNegativeBalanceEvent: Number(highlightedNegativeBalanceEvent),
        targetGroupIdentifier: targetGroupIdentifier.toString(),
      });
    }
  });

  /**
   * Clear all highlight query params from the current route.
   */
  async function clearHighlightsFromRoute(): Promise<void> {
    const { highlightedAssetMovement, highlightedNegativeBalanceEvent, highlightedPotentialMatch, ...remainingQuery } = get(route).query;
    if (highlightedAssetMovement || highlightedPotentialMatch || highlightedNegativeBalanceEvent) {
      await router.replace({ query: remainingQuery });
    }
  }

  /**
   * Build highlight query params from a navigation request.
   */
  function buildHighlightQuery(request: HistoryEventNavigationRequest, page: number): Record<string, string> {
    const query: Record<string, string> = { page: page.toString() };

    if (request.highlightedAssetMovement)
      query.highlightedAssetMovement = request.highlightedAssetMovement.toString();

    if (request.highlightedPotentialMatch)
      query.highlightedPotentialMatch = request.highlightedPotentialMatch.toString();

    if (request.highlightedNegativeBalanceEvent)
      query.highlightedNegativeBalanceEvent = request.highlightedNegativeBalanceEvent.toString();

    return query;
  }

  // Watch for composable-based navigation requests
  watchImmediate(pendingNavigation, async (request) => {
    if (!request)
      return;

    let currentRequest: HistoryEventNavigationRequest | undefined = request;

    try {
      while (currentRequest) {
        const filterPayload = currentRequest.preserveFilters && pageParams ? get(pageParams) : undefined;
        const position = await getHistoryEventGroupPosition(currentRequest.targetGroupIdentifier, filterPayload);

        // Check if this request is still current after the await
        if (get(pendingNavigation) !== request)
          return;

        if (position < 0) {
          // Target not in filtered results, try fallback
          if (currentRequest.fallbacks?.length) {
            const [next, ...remaining]: HistoryEventNavigationRequest[] = currentRequest.fallbacks;
            currentRequest = { ...next, fallbacks: remaining.length > 0 ? remaining : undefined };
            continue;
          }
          // No fallbacks left, clear highlights
          await clearHighlightsFromRoute();
          break;
        }

        const limit = get(pagination).limit;
        const page = Math.floor(position / limit) + 1;
        const highlightQuery = buildHighlightQuery(currentRequest, page);

        if (currentRequest.preserveFilters && groupLoading) {
          /**
           * Wait for the pagination system's loading cycle to complete.
           * The loading may not have started yet (fetchDebounce), so wait for it to start first.
           */
          if (!get(groupLoading)) {
            await until(groupLoading).toBe(true, { timeout: HIGHLIGHT_LOADING_START_TIMEOUT, throwOnTimeout: false });
          }
          // Now wait for loading to finish
          if (get(groupLoading)) {
            await until(groupLoading).toBe(false);
          }

          // Check if this request is still current after waiting
          if (get(pendingNavigation) !== request)
            return;

          // Route now has the correct filter/limit values from the pagination system
          await router.push({
            force: true,
            path: historyEventsPath,
            query: { ...get(route).query, ...highlightQuery },
          });
        }
        else {
          await router.push({
            force: true,
            path: historyEventsPath,
            query: { limit: limit.toString(), ...highlightQuery },
          });
        }
        break;
      }
    }
    catch (error: any) {
      // Only show notification for user-initiated navigation, not filter-change re-navigation
      if (!request.preserveFilters) {
        notify({
          display: true,
          message: error.message,
          title: t('asset_movement_matching.dialog.show_in_events'),
        });
      }
    }
    finally {
      consumeNavigation();
    }
  });
}
