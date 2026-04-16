import type { EvmUnDecodedTransactionsData } from '@/modules/core/messaging/types';

export interface DecodingStatusEntry extends EvmUnDecodedTransactionsData {
  cancelled?: boolean;
}

export const useDecodingStatusStore = defineStore('history/decoding-status', () => {
  const undecodedTransactionsStatus = shallowRef<Record<string, EvmUnDecodedTransactionsData>>({});
  const decodingSyncProgress = shallowRef<Record<string, DecodingStatusEntry>>({});
  const decodingSyncing = shallowRef<boolean>(false);

  const decodingStatus = computed<EvmUnDecodedTransactionsData[]>(() =>
    Object.values(get(undecodedTransactionsStatus)).filter(status => status.total > 0),
  );

  const decodingSyncStatus = computed<DecodingStatusEntry[]>(() =>
    Object.values(get(decodingSyncProgress)).filter(status => status.total > 0),
  );

  const setUndecodedTransactionsStatus = (data: EvmUnDecodedTransactionsData): void => {
    set(undecodedTransactionsStatus, {
      ...get(undecodedTransactionsStatus),
      [data.chain]: data,
    });

    if (!get(decodingSyncing))
      return;

    const currentSync = get(decodingSyncProgress);
    if (currentSync[data.chain]?.cancelled)
      return;

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

    if (!get(decodingSyncing))
      return;

    const currentSyncProgress = get(decodingSyncProgress);
    const updatedSyncProgress = { ...currentSyncProgress };
    let hasChanges = false;

    for (const [chain, status] of Object.entries(data)) {
      const existing = currentSyncProgress[chain];
      if (existing?.cancelled)
        continue;

      if (!existing || status.processed >= existing.processed) {
        updatedSyncProgress[chain] = status;
        hasChanges = true;
      }
    }

    if (hasChanges)
      set(decodingSyncProgress, updatedSyncProgress);
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

  const getUndecodedTransactionStatus = (): EvmUnDecodedTransactionsData[] =>
    Object.values(get(undecodedTransactionsStatus));

  return {
    decodingStatus,
    decodingSyncProgress,
    decodingSyncStatus,
    decodingSyncing,
    getUndecodedTransactionStatus,
    markDecodingCancelled,
    resetDecodingSyncProgress,
    resetUndecodedTransactionsStatus,
    setUndecodedTransactionsStatus,
    stopDecodingSyncProgress,
    undecodedTransactionsStatus,
    updateUndecodedTransactionsStatus,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useDecodingStatusStore, import.meta.hot));
