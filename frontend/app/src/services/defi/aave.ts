import { type PendingTask } from '@/services/types-api';
import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';

export const useAaveApi = () => {
  const fetchAaveBalances = async (): Promise<PendingTask> => {
    const url = '/blockchains/ETH/modules/aave/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchAaveHistory = async (reset?: boolean): Promise<PendingTask> => {
    const url = '/blockchains/ETH/modules/aave/history';
    const params = reset ? { resetDbData: true } : undefined;
    return fetchExternalAsync(api.instance, url, params);
  };

  return {
    fetchAaveBalances,
    fetchAaveHistory
  };
};
