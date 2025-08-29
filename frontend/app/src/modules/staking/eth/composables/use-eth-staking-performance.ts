import type { EthStakingPayload, EthStakingPerformance } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import { useEth2Staking } from '@/composables/staking/eth2/eth2';

interface UseEthStakingPerformanceReturn {
  getPerformance: () => { entriesTotal: number };
  performance: ComputedRef<EthStakingPerformance>;
  performanceLoading: Ref<boolean>;
  performancePagination: Ref<EthStakingPayload>;
  refreshPerformance: (userInitiated?: boolean) => Promise<void>;
}

export function useEthStakingPerformance(): UseEthStakingPerformanceReturn {
  const {
    pagination: performancePagination,
    performance,
    performanceLoading,
    refreshPerformance,
  } = useEth2Staking();

  async function refreshPerformanceWithReturn(userInitiated = false): Promise<void> {
    await refreshPerformance(userInitiated);
  }

  function getPerformance(): { entriesTotal: number } {
    const perf = get(performance);
    return { entriesTotal: perf?.entriesTotal ?? 0 };
  }

  return {
    getPerformance,
    performance,
    performanceLoading,
    performancePagination,
    refreshPerformance: refreshPerformanceWithReturn,
  };
}
