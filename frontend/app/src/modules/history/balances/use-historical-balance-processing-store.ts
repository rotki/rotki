import type { HistoricalBalanceProcessingPhase } from '@/modules/core/messaging/types/status-types';

export const useHistoricalBalanceProcessingStore = defineStore('history/historical-balance-processing', () => {
  const historicalBalanceProcessingCompleted = ref<number>(0);
  const historicalBalanceProcessingProgressed = ref<number>(0);
  const currentBalanceDetectionCompleted = ref<number>(0);
  /** The pass the running processing reported last; absent while none runs. */
  const processingPhase = ref<HistoricalBalanceProcessingPhase>();

  function notifyHistoricalBalanceProcessingCompleted(): void {
    set(processingPhase, undefined);
    set(historicalBalanceProcessingCompleted, get(historicalBalanceProcessingCompleted) + 1);
  }

  /** Counts the progress reports of a running pass, which may have stored part of its results. */
  function notifyHistoricalBalanceProcessingProgressed(phase: HistoricalBalanceProcessingPhase): void {
    set(processingPhase, phase);
    set(historicalBalanceProcessingProgressed, get(historicalBalanceProcessingProgressed) + 1);
  }

  function notifyCurrentBalanceDetectionCompleted(): void {
    set(currentBalanceDetectionCompleted, get(currentBalanceDetectionCompleted) + 1);
  }

  return {
    currentBalanceDetectionCompleted,
    historicalBalanceProcessingCompleted,
    historicalBalanceProcessingProgressed,
    notifyCurrentBalanceDetectionCompleted,
    notifyHistoricalBalanceProcessingCompleted,
    notifyHistoricalBalanceProcessingProgressed,
    processingPhase,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricalBalanceProcessingStore, import.meta.hot));
