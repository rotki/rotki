import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { PendingTask } from '@/types/task';

interface UseLiquityApiReturn {
  fetchLiquityBalances: () => Promise<PendingTask>;
  fetchLiquityStaking: () => Promise<PendingTask>;
  fetchLiquityStakingPools: () => Promise<PendingTask>;
  fetchLiquityStatistics: () => Promise<PendingTask>;
}

export function useLiquityApi(): UseLiquityApiReturn {
  const fetchLiquityBalances = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/liquity/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchLiquityStaking = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/liquity/staking';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchLiquityStakingPools = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/liquity/pool';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchLiquityStatistics = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/liquity/stats';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchLiquityBalances,
    fetchLiquityStaking,
    fetchLiquityStakingPools,
    fetchLiquityStatistics,
  };
}
