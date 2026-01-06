import type { HistoricalBalancesPayload } from '@/modules/history/balances/types';
import { useTaskApi } from '@/composables/api/task';
import { api } from '@/modules/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseHistoricalBalancesApiReturn {
  fetchHistoricalBalances: (payload: HistoricalBalancesPayload) => Promise<PendingTask>;
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

  const processHistoricalBalances = async (): Promise<PendingTask> =>
    triggerTask('historical_balance_processing');

  return {
    fetchHistoricalBalances,
    processHistoricalBalances,
  };
}
