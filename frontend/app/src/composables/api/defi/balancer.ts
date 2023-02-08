import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';

export const useBalancerApi = () => {
  const fetchBalancerBalances = async (): Promise<PendingTask> => {
    const url = 'blockchains/ETH/modules/balancer/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchBalancerEvents = async (): Promise<PendingTask> => {
    const url = '/blockchains/ETH/modules/balancer/history/events';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchBalancerBalances,
    fetchBalancerEvents
  };
};
