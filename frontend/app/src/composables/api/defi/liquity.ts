import type { PendingTask } from '@/types/task';
import { api } from '@/services/rotkehlchen-api';
import { fetchExternalAsync } from '@/services/utils';

interface UseLiquityApiReturn {
  fetchLiquityBalances: () => Promise<PendingTask>;
  fetchLiquityStaking: () => Promise<PendingTask>;
  fetchLiquityStakingPools: () => Promise<PendingTask>;
  fetchLiquityStatistics: () => Promise<PendingTask>;
}

export function useLiquityApi(): UseLiquityApiReturn {
  const fetchLiquityBalances = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/liquity/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchLiquityStaking = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/liquity/staking';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchLiquityStakingPools = async (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/liquity/pool';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchLiquityStatistics = async (): Promise<PendingTask> => {
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
