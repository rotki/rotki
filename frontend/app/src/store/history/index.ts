import type { EvmUnDecodedTransactionsData, ProtocolCacheUpdatesData } from '@/modules/messaging/types';
import type { LocationLabel } from '@/types/location';
import { useHistoryApi } from '@/composables/api/history';
import { type TransactionStatus, useHistoryEventsApi } from '@/composables/api/history/events';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

export const useHistoryStore = defineStore('history', () => {
  const associatedLocations = ref<string[]>([]);
  const locationLabels = ref<LocationLabel[]>([]);
  const undecodedTransactionsStatus = ref<Record<string, EvmUnDecodedTransactionsData>>({});
  const protocolCacheUpdateStatus = ref<Record<string, ProtocolCacheUpdatesData>>({});
  const transactionStatusSummary = ref<TransactionStatus>();

  // Separate state for sync progress indicator - only updated by websocket messages,
  // not reset by fetchUndecodedTransactionsBreakdown
  const decodingSyncProgress = ref<Record<string, EvmUnDecodedTransactionsData>>({});

  const receivingProtocolCacheStatus = ref<boolean>(false);

  const { useIsTaskRunning } = useTaskStore();
  const { getTransactionStatusSummary } = useHistoryEventsApi();

  const decodingStatus = computed<EvmUnDecodedTransactionsData[]>(() =>
    Object.values(get(undecodedTransactionsStatus)).filter(status => status.total > 0),
  );

  // Computed for sync progress indicator - uses the separate sync progress state
  const decodingSyncStatus = computed<EvmUnDecodedTransactionsData[]>(() =>
    Object.values(get(decodingSyncProgress)).filter(status => status.total > 0),
  );

  const protocolCacheStatus = computed<ProtocolCacheUpdatesData[]>(() =>
    Object.values(get(protocolCacheUpdateStatus)).filter(status => status.total > 0),
  );

  const setUndecodedTransactionsStatus = (data: EvmUnDecodedTransactionsData): void => {
    set(receivingProtocolCacheStatus, false);
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      [data.chain]: data,
    });
    // Also update sync progress state (used by sync progress indicator)
    set(decodingSyncProgress, {
      ...get(decodingSyncProgress),
      [data.chain]: data,
    });
  };

  const updateUndecodedTransactionsStatus = (data: Record<string, EvmUnDecodedTransactionsData>): void => {
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      ...data,
    });

    // Also update sync progress, but only if:
    // 1. The chain doesn't exist in sync progress yet (initialization), OR
    // 2. The new data has equal or higher processed count (progress update, not reset)
    const currentSyncProgress = get(decodingSyncProgress);
    const updatedSyncProgress = { ...currentSyncProgress };
    let hasChanges = false;

    for (const [chain, status] of Object.entries(data)) {
      const existing = currentSyncProgress[chain];
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
    const filtered: Record<string, ProtocolCacheUpdatesData> = {};
    const currentKey = `${data.chain}#${data.protocol}`;
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

  const resetUndecodedTransactionsStatus = (): void => {
    set(undecodedTransactionsStatus, {});
  };

  const clearUndecodedTransactionsNumbers = (): void => {
    set(undecodedTransactionsStatus, {});
  };

  const resetDecodingSyncProgress = (): void => {
    set(decodingSyncProgress, {});
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
    if (!curr && prev) {
      resetProtocolCacheUpdatesStatus();
    }
  });

  return {
    associatedLocations,
    clearUndecodedTransactionsNumbers,
    decodingStatus,
    decodingSyncProgress,
    decodingSyncStatus,
    fetchAssociatedLocations,
    fetchLocationLabels,
    fetchTransactionStatusSummary,
    getUndecodedTransactionStatus,
    locationLabels,
    protocolCacheStatus,
    receivingProtocolCacheStatus,
    resetDecodingSyncProgress,
    resetProtocolCacheUpdatesStatus,
    resetUndecodedTransactionsStatus,
    setProtocolCacheStatus,
    setUndecodedTransactionsStatus,
    transactionStatusSummary,
    undecodedTransactionsStatus,
    updateUndecodedTransactionsStatus,
  };
});
