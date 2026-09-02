import type { NegativeBalanceDetectedData } from '@/modules/core/messaging/types/status-types';

/**
 * Negative-balance findings reported during historical-balance processing.
 *
 * @remarks
 * Findings only. Processing progress belongs on the HISTORICAL_BALANCES orchestrator activity,
 * not here.
 */
export const useHistoricalBalancesStore = defineStore('balances/historical', () => {
  const negativeBalances = ref<NegativeBalanceDetectedData[]>([]);

  /**
   * Records one negative balance reported by the accounting run.
   *
   * @remarks
   * These arrive one at a time and accumulate. A differing `lastRunTs` means a later run is
   * reporting, so its findings replace the previous run's rather than joining them.
   */
  function addNegativeBalance(data: NegativeBalanceDetectedData): void {
    const current = get(negativeBalances);

    if (current.length > 0 && current[0].lastRunTs !== data.lastRunTs) {
      set(negativeBalances, [data]);
      return;
    }

    set(negativeBalances, [...current, data]);
  }

  return {
    addNegativeBalance,
    negativeBalances,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricalBalancesStore, import.meta.hot));
