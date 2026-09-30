export const useHistoricalBalanceProcessingStore = defineStore('history/historical-balance-processing', () => {
  const historicalBalanceProcessingCompleted = ref<number>(0);

  function notifyHistoricalBalanceProcessingCompleted(): void {
    set(historicalBalanceProcessingCompleted, get(historicalBalanceProcessingCompleted) + 1);
  }

  return {
    historicalBalanceProcessingCompleted,
    notifyHistoricalBalanceProcessingCompleted,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricalBalanceProcessingStore, import.meta.hot));
