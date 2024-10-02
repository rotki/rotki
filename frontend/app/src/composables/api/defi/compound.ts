import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { PendingTask } from '@/types/task';

interface UseCompoundApiReturn {
  fetchCompoundBalances: () => Promise<PendingTask>;
  fetchCompoundStats: () => Promise<PendingTask>;
}

export function useCompoundApi(): UseCompoundApiReturn {
  const fetchCompoundBalances = async (): Promise<PendingTask> => {
    const url = '/blockchains/eth/modules/compound/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchCompoundStats = async (): Promise<PendingTask> => {
    const url = '/blockchains/eth/modules/compound/stats';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchCompoundBalances,
    fetchCompoundStats,
  };
}
