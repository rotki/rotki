import type { ProtocolCacheUpdatesData } from '@/modules/core/messaging/types';

export interface ProtocolCacheStatusEntry extends ProtocolCacheUpdatesData {
  cancelled?: boolean;
}

export const useProtocolCacheStatusStore = defineStore('history/protocol-cache-status', () => {
  const protocolCacheUpdateStatus = shallowRef<Record<string, ProtocolCacheStatusEntry>>({});
  const receivingProtocolCacheStatus = ref<boolean>(false);

  const protocolCacheStatus = computed<ProtocolCacheStatusEntry[]>(() =>
    Object.values(get(protocolCacheUpdateStatus)).filter(status => status.total > 0),
  );

  const setProtocolCacheStatus = (data: ProtocolCacheUpdatesData): void => {
    set(receivingProtocolCacheStatus, true);
    const old = get(protocolCacheUpdateStatus);
    const currentKey = `${data.chain}#${data.protocol}`;

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

  const markAllProtocolCacheCancelled = (): void => {
    const current = get(protocolCacheUpdateStatus);
    const updated: Record<string, ProtocolCacheStatusEntry> = {};
    for (const [key, entry] of Object.entries(current)) {
      updated[key] = { ...entry, cancelled: true };
    }
    set(protocolCacheUpdateStatus, updated);
  };

  const resetProtocolCacheUpdatesStatus = (): void => {
    set(protocolCacheUpdateStatus, {});
    set(receivingProtocolCacheStatus, false);
  };

  const setReceivingProtocolCacheStatus = (value: boolean): void => {
    set(receivingProtocolCacheStatus, value);
  };

  return {
    markAllProtocolCacheCancelled,
    protocolCacheStatus,
    protocolCacheUpdateStatus,
    receivingProtocolCacheStatus,
    resetProtocolCacheUpdatesStatus,
    setProtocolCacheStatus,
    setReceivingProtocolCacheStatus,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useProtocolCacheStatusStore, import.meta.hot));
