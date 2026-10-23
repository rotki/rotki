export const useHistoricalBalanceProcessingStore = defineStore('history/historical-balance-processing', () => {
  const historicalBalanceProcessingCompleted = ref<number>(0);
  const currentBalanceDetectionCompleted = ref<number>(0);

  function notifyHistoricalBalanceProcessingCompleted(): void {
    set(historicalBalanceProcessingCompleted, get(historicalBalanceProcessingCompleted) + 1);
  }

  function notifyCurrentBalanceDetectionCompleted(): void {
    set(currentBalanceDetectionCompleted, get(currentBalanceDetectionCompleted) + 1);
  }

  return {
    currentBalanceDetectionCompleted,
    historicalBalanceProcessingCompleted,
    notifyCurrentBalanceDetectionCompleted,
    notifyHistoricalBalanceProcessingCompleted,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricalBalanceProcessingStore, import.meta.hot));
