import type { NegativeBalanceDetectedData } from '@/modules/core/messaging/types/status-types';

/**
 * Negative-balance findings reported during historical-balance processing. Processing *progress*
 * is no longer kept here — it lives on the native HISTORICAL_BALANCES orchestrator activity (the
 * websocket handler pushes it via `reportProgress`); this store only accumulates the per-run
 * negative balances, resetting whenever a new run (`lastRunTs`) begins.
 */
export const useHistoricalBalancesStore = defineStore('balances/historical', () => {
  const negativeBalances = ref<NegativeBalanceDetectedData[]>([]);

  function addNegativeBalance(data: NegativeBalanceDetectedData): void {
    const current = get(negativeBalances);

    // If the array is not empty and the lastRunTs is different, clear and start fresh
    if (current.length > 0 && current[0].lastRunTs !== data.lastRunTs) {
      set(negativeBalances, [data]);
      return;
    }

    // Accumulate the new data
    set(negativeBalances, [...current, data]);
  }

  return {
    addNegativeBalance,
    negativeBalances,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricalBalancesStore, import.meta.hot));
