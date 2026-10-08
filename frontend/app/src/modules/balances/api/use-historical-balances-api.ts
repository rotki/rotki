import { FetchError } from 'ofetch';
import { api } from '@/modules/core/api/rotki-api';
import { HTTPStatus } from '@/modules/core/api/types/http';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import {
  type HistoricalBalanceDivergencePayload,
  HistoricalBalancesAtEventsResponse,
  type HistoricalBalanceSeriesPayload,
  HistoricalBalancesResponse,
} from '@/modules/history/balances/types';

interface UseHistoricalBalancesApiReturn {
  fetchHistoricalBalances: (timestamp: number) => Promise<HistoricalBalancesResponse>;
  fetchHistoricalBalancesAtEvents: (eventIdentifiers: number[]) => Promise<HistoricalBalancesAtEventsResponse>;
  findHistoricalBalanceDivergence: (payload: HistoricalBalanceDivergencePayload) => Promise<PendingTask>;
  fetchHistoricalBalanceSeries: (payload: HistoricalBalanceSeriesPayload) => Promise<PendingTask>;
  processHistoricalBalances: () => Promise<PendingTask>;
}

export function useHistoricalBalancesApi(): UseHistoricalBalancesApiReturn {
  const { triggerTask } = useTaskApi();

  /**
   * Every account's balance of every asset at `timestamp`, one entry per bucket.
   *
   * @remarks
   * Synchronous on purpose: the backend answers a date with no holdings with a 404, which only a
   * direct request can tell apart from a failure. Under an async task it would arrive as a failed
   * task with nothing but its message.
   *
   * @param timestamp - unix seconds
   */
  async function fetchHistoricalBalances(timestamp: number): Promise<HistoricalBalancesResponse> {
    try {
      return HistoricalBalancesResponse.parse(await api.post('/balances/historical', { groupByAccount: true, timestamp }));
    }
    catch (error: unknown) {
      if (error instanceof FetchError && error.status === HTTPStatus.NOT_FOUND)
        return { entries: [], processingRequired: false };
      throw error;
    }
  }

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
    fetchHistoricalBalances,
    fetchHistoricalBalancesAtEvents,
    findHistoricalBalanceDivergence,
    fetchHistoricalBalanceSeries,
    processHistoricalBalances,
  };
}
