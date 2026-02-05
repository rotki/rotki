import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef } from 'vue';
import { startPromise } from '@shared/utils';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { Routes } from '@/router/routes';
import { useNotificationsStore } from '@/store/notifications';

export interface HistoryEventNavigationRequest {
  /** Group to navigate to (used for getHistoryEventGroupPosition API call) */
  targetGroupIdentifier: string;
  /** Event ID for selected asset movement highlight (warning/yellow) */
  highlightedAssetMovement?: number;
  /** Event ID for potential match highlight (success/green) */
  highlightedPotentialMatch?: number;
  /** Event ID for negative balance highlight (error/red) */
  highlightedNegativeBalanceEvent?: number;
}

const historyEventsPath = Routes.HISTORY_EVENTS.toString();
const pendingNavigation = ref<HistoryEventNavigationRequest>();
const isNavigating = ref<boolean>(false);

export const useHistoryEventNavigation = createSharedComposable(() => {
  const router = useRouter();
  const route = useRoute();

  function requestNavigation(request: HistoryEventNavigationRequest): void {
    set(isNavigating, true);
    set(pendingNavigation, request);

    // If not on the history events page, navigate there first.
    // The consumer will pick up the pending request via watchImmediate when it mounts.
    if (!get(route).path.startsWith(historyEventsPath)) {
      startPromise(router.push({ path: historyEventsPath }));
    }
  }

  function consumeNavigation(): void {
    set(pendingNavigation, undefined);
    set(isNavigating, false);
  }

  return { consumeNavigation, isNavigating, pendingNavigation, requestNavigation };
});

/**
 * Sets up watchers that consume pending navigation requests.
 * Should be called once from HistoryEventsView to handle navigation
 * from any producer (e.g., MatchAssetMovementsPinned, NegativeBalancesDialog, external packages).
 *
 * Supports two input channels:
 * 1. Composable-based: internal components call requestNavigation() directly
 * 2. Route-based: external packages push route with targetGroupIdentifier + highlight query params (e.g., highlightedNegativeBalanceEvent)
 */
export function useHistoryEventNavigationConsumer(pagination: ComputedRef<TablePaginationData>): void {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const route = useRoute();
  const { getHistoryEventGroupPosition } = useHistoryEventsApi();
  const { consumeNavigation, pendingNavigation, requestNavigation } = useHistoryEventNavigation();
  const { notify } = useNotificationsStore();

  // Watch for route-based navigation from external packages
  watchImmediate(route, ({ query }) => {
    const { targetGroupIdentifier, highlightedNegativeBalanceEvent } = query;
    if (targetGroupIdentifier && highlightedNegativeBalanceEvent) {
      requestNavigation({
        highlightedNegativeBalanceEvent: Number(highlightedNegativeBalanceEvent),
        targetGroupIdentifier: targetGroupIdentifier.toString(),
      });
    }
  });

  // Watch for composable-based navigation requests
  watchImmediate(pendingNavigation, async (request) => {
    if (!request)
      return;

    try {
      const position = await getHistoryEventGroupPosition(request.targetGroupIdentifier);
      // Check if this request is still current after the await
      if (get(pendingNavigation) !== request)
        return;

      const limit = get(pagination).limit;
      const page = Math.floor(position / limit) + 1;

      const query: Record<string, string> = {
        limit: limit.toString(),
        page: page.toString(),
      };

      if (request.highlightedAssetMovement)
        query.highlightedAssetMovement = request.highlightedAssetMovement.toString();

      if (request.highlightedPotentialMatch)
        query.highlightedPotentialMatch = request.highlightedPotentialMatch.toString();

      if (request.highlightedNegativeBalanceEvent)
        query.highlightedNegativeBalanceEvent = request.highlightedNegativeBalanceEvent.toString();

      await router.push({
        force: true,
        path: historyEventsPath,
        query,
      });
    }
    catch (error: any) {
      notify({
        display: true,
        message: error.message,
        title: t('asset_movement_matching.dialog.show_in_events'),
      });
    }
    finally {
      consumeNavigation();
    }
  });
}
