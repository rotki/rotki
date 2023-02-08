import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';

export const useLiquityApi = () => {
  const fetchLiquityBalances = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/liquity/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchLiquityStaking = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/liquity/staking';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchLiquityStakingPools = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/liquity/pool';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchLiquityBalances,
    fetchLiquityStaking,
    fetchLiquityStakingPools
  };
};
