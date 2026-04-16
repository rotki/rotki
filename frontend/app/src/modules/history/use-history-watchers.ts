import { NotificationGroup } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { isEqual } from 'es-toolkit';
import { useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';
import { useRefWithDebounce } from '@/composables/ref';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { useProtocolCacheStatusStore } from '@/modules/history/use-protocol-cache-status-store';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { useSessionSettingsStore } from '@/modules/settings/use-session-settings-store';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskStore } from '@/modules/tasks/use-task-store';
import { Routes } from '@/router/routes';

const HISTORY_EVENTS_MODIFIED_DEBOUNCE_MS = 15_000;

export function useHistoryWatchers(): void {
  const { processing } = useHistoryEventsStatus();
  const { fetchTransactionStatusSummary } = useHistoryDataFetching();
  const historyStore = useHistoryStore();
  const { hasUnprocessedModifications } = storeToRefs(historyStore);
  const { triggerAssetMovementAutoMatching } = useUnmatchedAssetMovements();
  const { triggerHistoricalBalancesProcessing } = useHistoricalBalances();
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { removeMatching } = useNotifications();
  const router = useRouter();

  const processingDebounced = useRefWithDebounce(processing, 500);

  // Protocol cache status reset when refresh task completes
  const { useIsTaskRunning } = useTaskStore();
  const refreshProtocolCacheTaskRunning = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
  const protocolCacheStore = useProtocolCacheStatusStore();
  const { protocolCacheUpdateStatus } = storeToRefs(protocolCacheStore);

  watch(refreshProtocolCacheTaskRunning, (curr, prev) => {
    if (!curr && prev && !Object.values(get(protocolCacheUpdateStatus)).some(entry => entry.cancelled)) {
      protocolCacheStore.resetProtocolCacheUpdatesStatus();
    }
  });

  // Debounced reprocessing after manual event modifications
  watchDebounced(
    () => historyStore.eventsVersion,
    () => {
      if (get(hasUnprocessedModifications)) {
        historyStore.acknowledgeModifications();
        startPromise(triggerHistoricalBalancesProcessing());
      }
    },
    { debounce: HISTORY_EVENTS_MODIFIED_DEBOUNCE_MS },
  );

  watch([processing, connectedExchanges], async ([currentProcessing, connectedExchanges], [previousProcessing, previousConnectedExchanges]) => {
    if (currentProcessing !== previousProcessing || !isEqual(connectedExchanges, previousConnectedExchanges)) {
      await fetchTransactionStatusSummary();
    }
  });

  watch(processingDebounced, async (processing, wasProcessing) => {
    if (!processing && wasProcessing) {
      historyStore.acknowledgeModifications();
      await triggerHistoricalBalancesProcessing();
      await triggerAssetMovementAutoMatching();
    }
  });

  watchImmediate(router.currentRoute, (to) => {
    if (to.path === Routes.HISTORY_EVENTS.toString()) {
      removeMatching(notification => notification.group === NotificationGroup.UNMATCHED_ASSET_MOVEMENTS);
    }
  });
}
