import type { HistoricalBalanceSeriesPayload } from '@/modules/history/balances/types';
import { api } from '@/modules/core/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';

interface UseHistoricalBalancesApiReturn {
  fetchHistoricalBalanceSeries: (payload: HistoricalBalanceSeriesPayload) => Promise<PendingTask>;
  processHistoricalBalances: () => Promise<PendingTask>;
}

export function useHistoricalBalancesApi(): UseHistoricalBalancesApiReturn {
  const { triggerTask } = useTaskApi();

  const fetchHistoricalBalanceSeries = async (payload: HistoricalBalanceSeriesPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/balances/historical/asset/series', {
      asyncQuery: true,
      ...payload,
    });
    return PendingTaskSchema.parse(response);
  };

  const processHistoricalBalances = async (): Promise<PendingTask> =>
    triggerTask('historical_balance_processing');

  return {
    fetchHistoricalBalanceSeries,
    processHistoricalBalances,
  };
}
