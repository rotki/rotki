import type { HistoricalBalancesPayload } from '@/types/balances';
import { api } from '@/modules/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseHistoricalBalancesApiReturn {
  fetchHistoricalBalances: (payload: HistoricalBalancesPayload) => Promise<PendingTask>;
  processHistoricalBalances: () => Promise<PendingTask>;
}

export function useHistoricalBalancesApi(): UseHistoricalBalancesApiReturn {
  const fetchHistoricalBalances = async (payload: HistoricalBalancesPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/balances/historical', {
      asyncQuery: true,
      ...payload,
    });
    return PendingTaskSchema.parse(response);
  };

  const processHistoricalBalances = async (): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/balances/historical/process', {
      asyncQuery: true,
    });
    return PendingTaskSchema.parse(response);
  };

  return {
    fetchHistoricalBalances,
    processHistoricalBalances,
  };
}
