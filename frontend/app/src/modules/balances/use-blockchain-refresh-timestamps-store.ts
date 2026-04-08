import type { ComputedRef } from 'vue';

export const useBlockchainRefreshTimestampsStore = defineStore('balances/refresh-timestamps', () => {
  const refreshTimestamps = ref<Record<string, number>>({});

  const updateTimestamps = (timestamps: Record<string, number>): void => {
    set(refreshTimestamps, { ...get(refreshTimestamps), ...timestamps });
  };

  const getTimestamp = (chain: string): ComputedRef<number | undefined> =>
    computed<number | undefined>(() => get(refreshTimestamps)[chain]);

  const reset = (): void => {
    set(refreshTimestamps, {});
  };

  return { getTimestamp, refreshTimestamps, reset, updateTimestamps };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainRefreshTimestampsStore, import.meta.hot));
