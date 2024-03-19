import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { PendingTask } from '@/types/task';

export function useAaveApi() {
  const fetchAaveBalances = (): Promise<PendingTask> => {
    const url = '/blockchains/eth/modules/aave/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchAaveHistory = (): Promise<PendingTask> => {
    const url = '/blockchains/eth/modules/aave/stats';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchAaveBalances,
    fetchAaveHistory,
  };
}
