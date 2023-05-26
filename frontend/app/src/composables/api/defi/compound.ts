import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/types/task';

export const useCompoundApi = () => {
  const fetchCompoundBalances = async (): Promise<PendingTask> => {
    const url = '/blockchains/eth/modules/compound/balances';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchCompoundHistory = async (): Promise<PendingTask> => {
    const url = '/blockchains/eth/modules/compound/history';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchCompoundBalances,
    fetchCompoundHistory
  };
};
