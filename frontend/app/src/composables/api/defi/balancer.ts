import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { PendingTask } from '@/types/task';

interface UseBalancerApiReturn { fetchBalancerBalances: () => Promise<PendingTask> }

export function useBalancerApi(): UseBalancerApiReturn {
  const fetchBalancerBalances = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/balancer/balances';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchBalancerBalances,
  };
}
