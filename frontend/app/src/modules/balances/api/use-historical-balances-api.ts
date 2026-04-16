import type { HistoricalBalancesPayload, OnchainHistoricalBalancePayload } from '@/modules/history/balances/types';
import { api } from '@/modules/core/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';

interface UseHistoricalBalancesApiReturn {
  fetchHistoricalBalances: (payload: HistoricalBalancesPayload) => Promise<PendingTask>;
  fetchOnchainHistoricalBalance: (payload: OnchainHistoricalBalancePayload) => Promise<PendingTask>;
  processHistoricalBalances: () => Promise<PendingTask>;
}

export function useHistoricalBalancesApi(): UseHistoricalBalancesApiReturn {
  const { triggerTask } = useTaskApi();

  const fetchHistoricalBalances = async (payload: HistoricalBalancesPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/balances/historical', {
      asyncQuery: true,
      ...payload,
    });
    return PendingTaskSchema.parse(response);
  };

  const fetchOnchainHistoricalBalance = async (payload: OnchainHistoricalBalancePayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/balances/historical/onchain', {
      asyncQuery: true,
      ...payload,
    });
    return PendingTaskSchema.parse(response);
  };

  const processHistoricalBalances = async (): Promise<PendingTask> =>
    triggerTask('historical_balance_processing');

  return {
    fetchHistoricalBalances,
    fetchOnchainHistoricalBalance,
    processHistoricalBalances,
  };
}
