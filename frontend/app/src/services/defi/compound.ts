import { type PendingTask } from '@/services/types-api';
import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';

export const useCompoundApi = () => {
  const fetchCompoundBalances = async (): Promise<PendingTask> => {
    const url = '/blockchains/ETH/modules/compound/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchCompoundHistory = async (): Promise<PendingTask> => {
    const url = '/blockchains/ETH/modules/compound/history';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchCompoundBalances,
    fetchCompoundHistory
  };
};
