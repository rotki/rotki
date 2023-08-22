import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';

export const useAaveApi = () => {
  const fetchAaveBalances = async (): Promise<PendingTask> => {
    const url = '/blockchains/eth/modules/aave/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchAaveHistory = async (): Promise<PendingTask> => {
    const url = '/blockchains/eth/modules/aave/stats';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchAaveBalances,
    fetchAaveHistory
  };
};
