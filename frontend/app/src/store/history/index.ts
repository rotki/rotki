import type { EvmUnDecodedTransactionsData, ProtocolCacheUpdatesData } from '@/modules/messaging/types';
import type { LocationLabel } from '@/types/location';
import { startPromise } from '@shared/utils';
import { useHistoryApi } from '@/composables/api/history';
import { type TransactionStatus, useHistoryEventsApi } from '@/composables/api/history/events';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

const HISTORY_EVENTS_MODIFIED_DEBOUNCE_MS = 15000;

export interface DecodingStatusEntry extends EvmUnDecodedTransactionsData {
  cancelled?: boolean;
}

export interface ProtocolCacheStatusEntry extends ProtocolCacheUpdatesData {
  cancelled?: boolean;
}

export const useHistoryStore = defineStore('history', () => {
  const associatedLocations = ref<string[]>([]);
  const locationLabels = ref<LocationLabel[]>([]);
  const undecodedTransactionsStatus = ref<Record<string, EvmUnDecodedTransactionsData>>({});
  const protocolCacheUpdateStatus = ref<Record<string, ProtocolCacheStatusEntry>>({});
  const transactionStatusSummary = ref<TransactionStatus>();
  const eventsModificationCounter = ref<number>(0);

  // Separate state for sync progress indicator - only updated by websocket messages,
  // not reset by fetchUndecodedTransactionsBreakdown
  const decodingSyncProgress = ref<Record<string, DecodingStatusEntry>>({});
  const decodingSyncing = ref<boolean>(false);

  const receivingProtocolCacheStatus = ref<boolean>(false);

  const { useIsTaskRunning } = useTaskStore();
  const { getTransactionStatusSummary } = useHistoryEventsApi();

  const decodingStatus = computed<EvmUnDecodedTransactionsData[]>(() =>
    Object.values(get(undecodedTransactionsStatus)).filter(status => status.total > 0),
  );

  // Computed for sync progress indicator - uses the separate sync progress state
  const decodingSyncStatus = computed<DecodingStatusEntry[]>(() =>
    Object.values(get(decodingSyncProgress)).filter(status => status.total > 0),
  );

  const protocolCacheStatus = computed<ProtocolCacheStatusEntry[]>(() =>
    Object.values(get(protocolCacheUpdateStatus)).filter(status => status.total > 0),
  );

  const setUndecodedTransactionsStatus = (data: EvmUnDecodedTransactionsData): void => {
    set(receivingProtocolCacheStatus, false);
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      [data.chain]: data,
    });
    // Only update sync progress when a user-initiated sync is active
    if (!get(decodingSyncing))
      return;

    // Guard: don't overwrite cancelled entries
    const currentSync = get(decodingSyncProgress);
    if (currentSync[data.chain]?.cancelled) {
      return;
    }
    set(decodingSyncProgress, {
      ...currentSync,
      [data.chain]: data,
    });
  };

  const updateUndecodedTransactionsStatus = (data: Record<string, EvmUnDecodedTransactionsData>): void => {
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      ...data,
    });

    // Only update sync progress when a user-initiated sync is active
    if (!get(decodingSyncing))
      return;

    // Also update sync progress, but only if:
    // 1. The chain doesn't exist in sync progress yet (initialization), OR
    // 2. The new data has equal or higher processed count (progress update, not reset)
    // 3. The chain is not cancelled
    const currentSyncProgress = get(decodingSyncProgress);
    const updatedSyncProgress = { ...currentSyncProgress };
    let hasChanges = false;

    for (const [chain, status] of Object.entries(data)) {
      const existing = currentSyncProgress[chain];
      // Skip cancelled entries
      if (existing?.cancelled)
        continue;

      // Initialize if not exists, or update if not a reset (processed going backwards)
      if (!existing || status.processed >= existing.processed) {
        updatedSyncProgress[chain] = status;
        hasChanges = true;
      }
    }

    if (hasChanges) {
      set(decodingSyncProgress, updatedSyncProgress);
    }
  };

  const refreshProtocolCacheTaskRunning = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);

  const setProtocolCacheStatus = (data: ProtocolCacheUpdatesData): void => {
    set(receivingProtocolCacheStatus, true);
    const old = get(protocolCacheUpdateStatus);
    const currentKey = `${data.chain}#${data.protocol}`;

    // Guard: don't overwrite cancelled entries
    if (old[currentKey]?.cancelled)
      return;

    const filtered: Record<string, ProtocolCacheStatusEntry> = {};
    for (const key in old) {
      if (key !== currentKey) {
        filtered[key] = {
          ...old[key],
          processed: old[key].total,
        };
      }
    }
    set(protocolCacheUpdateStatus, {
      [currentKey]: data,
      ...filtered,
    });
  };

  const markDecodingCancelled = (chain: string): void => {
    const current = get(decodingSyncProgress);
    const existing = current[chain];
    if (existing) {
      set(decodingSyncProgress, {
        ...current,
        [chain]: { ...existing, cancelled: true },
      });
    }
  };

  const markAllProtocolCacheCancelled = (): void => {
    const current = get(protocolCacheUpdateStatus);
    const updated: Record<string, ProtocolCacheStatusEntry> = {};
    for (const [key, entry] of Object.entries(current)) {
      updated[key] = { ...entry, cancelled: true };
    }
    set(protocolCacheUpdateStatus, updated);
  };

  const resetUndecodedTransactionsStatus = (): void => {
    set(undecodedTransactionsStatus, {});
  };

  const resetDecodingSyncProgress = (): void => {
    set(decodingSyncProgress, {});
    set(decodingSyncing, true);
  };

  const stopDecodingSyncProgress = (): void => {
    set(decodingSyncing, false);
  };

  const resetProtocolCacheUpdatesStatus = (): void => {
    set(protocolCacheUpdateStatus, {});
    set(receivingProtocolCacheStatus, false);
  };

  const { fetchAssociatedLocations: fetchAssociatedLocationsApi, fetchLocationLabels: fetchLocationLabelsApi } = useHistoryApi();
  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });

  const getUndecodedTransactionStatus = (): EvmUnDecodedTransactionsData[] =>
    Object.values(get(undecodedTransactionsStatus));

  const fetchAssociatedLocations = async (): Promise<void> => {
    try {
      set(associatedLocations, await fetchAssociatedLocationsApi());
    }
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        display: true,
        message: t('actions.history.fetch_associated_locations.error.message', { message }),
        title: t('actions.history.fetch_associated_locations.error.title'),
      });
    }
  };

  const fetchTransactionStatusSummary = async (): Promise<void> => {
    try {
      const result = await getTransactionStatusSummary();
      set(transactionStatusSummary, result);
    }
    catch (error: any) {
      logger.error(error);
    }
  };

  const fetchLocationLabels = async (): Promise<void> => {
    try {
      set(locationLabels, await fetchLocationLabelsApi());
    }
    catch (error: any) {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        display: true,
        message: t('actions.history.fetch_location_labels.error.message', { message }),
        title: t('actions.history.fetch_location_labels.error.title'),
      });
    }
  };

  watch(refreshProtocolCacheTaskRunning, (curr, prev) => {
    if (!curr && prev && !Object.values(get(protocolCacheUpdateStatus)).some(entry => entry.cancelled)) {
      resetProtocolCacheUpdatesStatus();
    }
  });

  function signalEventsModified(): void {
    set(eventsModificationCounter, get(eventsModificationCounter) + 1);
  }

  function resetEventsModifiedSignal(): void {
    set(eventsModificationCounter, 0);
  }

  const { triggerHistoricalBalancesProcessing } = useHistoricalBalances();

  watchDebounced(
    eventsModificationCounter,
    (counter) => {
      if (counter > 0) {
        startPromise(triggerHistoricalBalancesProcessing());
      }
    },
    { debounce: HISTORY_EVENTS_MODIFIED_DEBOUNCE_MS },
  );

  return {
    associatedLocations,
    decodingStatus,
    decodingSyncProgress,
    decodingSyncStatus,
    decodingSyncing,
    eventsModificationCounter,
    fetchAssociatedLocations,
    fetchLocationLabels,
    fetchTransactionStatusSummary,
    getUndecodedTransactionStatus,
    locationLabels,
    markAllProtocolCacheCancelled,
    markDecodingCancelled,
    protocolCacheStatus,
    receivingProtocolCacheStatus,
    resetDecodingSyncProgress,
    resetEventsModifiedSignal,
    resetProtocolCacheUpdatesStatus,
    resetUndecodedTransactionsStatus,
    setProtocolCacheStatus,
    setUndecodedTransactionsStatus,
    signalEventsModified,
    stopDecodingSyncProgress,
    transactionStatusSummary,
    undecodedTransactionsStatus,
    updateUndecodedTransactionsStatus,
  };
});
