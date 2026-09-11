import { api } from '@/modules/core/api/rotki-api';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import { type HistoricalBalanceDivergencePayload, HistoricalBalancesAtEventsResponse, type HistoricalBalanceSeriesPayload } from '@/modules/history/balances/types';

interface UseHistoricalBalancesApiReturn {
  fetchHistoricalBalancesAtEvents: (eventIdentifiers: number[]) => Promise<HistoricalBalancesAtEventsResponse>;
  findHistoricalBalanceDivergence: (payload: HistoricalBalanceDivergencePayload) => Promise<PendingTask>;
  fetchHistoricalBalanceSeries: (payload: HistoricalBalanceSeriesPayload) => Promise<PendingTask>;
  processHistoricalBalances: () => Promise<PendingTask>;
}

export function useHistoricalBalancesApi(): UseHistoricalBalancesApiReturn {
  const { triggerTask } = useTaskApi();

  async function fetchHistoricalBalancesAtEvents(eventIdentifiers: number[]): Promise<HistoricalBalancesAtEventsResponse> {
    return HistoricalBalancesAtEventsResponse.parse(await api.post('/balances/historical/events', { eventIdentifiers }));
  }

  const findHistoricalBalanceDivergence = async (payload: HistoricalBalanceDivergencePayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/balances/historical/onchain/divergence', {
      asyncQuery: true,
      ...payload,
    });
    return PendingTaskSchema.parse(response);
  };

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
    fetchHistoricalBalancesAtEvents,
    findHistoricalBalanceDivergence,
    fetchHistoricalBalanceSeries,
    processHistoricalBalances,
  };
}
