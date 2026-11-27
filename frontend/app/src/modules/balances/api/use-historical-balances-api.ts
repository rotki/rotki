import { FetchError } from 'ofetch';
import { api } from '@/modules/core/api/rotki-api';
import { HTTPStatus } from '@/modules/core/api/types/http';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import {
  CurrentHistoricalBalancesResponse,
  type HistoricalBalanceAssetsPayload,
  HistoricalBalanceAssetsResponse,
  type HistoricalBalanceDivergencePayload,
  type HistoricalBalanceFilters,
  HistoricalBalancesAtEventsResponse,
  type HistoricalBalanceSeriesPayload,
  HistoricalBalanceSeriesResponse,
  HistoricalBalancesResponse,
} from '@/modules/history/balances/types';

interface UseHistoricalBalancesApiReturn {
  fetchBalanceSeries: (payload: HistoricalBalanceSeriesPayload) => Promise<HistoricalBalanceSeriesResponse>;
  fetchCurrentHistoricalBalances: () => Promise<CurrentHistoricalBalancesResponse>;
  fetchHistoricalBalanceAssets: (payload: HistoricalBalanceAssetsPayload) => Promise<HistoricalBalanceAssetsResponse>;
  fetchHistoricalBalances: (timestamp: number, filters?: HistoricalBalanceFilters) => Promise<HistoricalBalancesResponse>;
  fetchHistoricalBalancesAtEvents: (eventIdentifiers: number[]) => Promise<HistoricalBalancesAtEventsResponse>;
  findHistoricalBalanceDivergence: (payload: HistoricalBalanceDivergencePayload) => Promise<PendingTask>;
  fetchHistoricalBalanceSeries: (payload: HistoricalBalanceSeriesPayload) => Promise<PendingTask>;
  processHistoricalBalances: () => Promise<PendingTask>;
}

function isNotFound(error: unknown): boolean {
  return error instanceof FetchError && error.status === HTTPStatus.NOT_FOUND;
}

export function useHistoricalBalancesApi(): UseHistoricalBalancesApiReturn {
  const { triggerTask } = useTaskApi();

  /**
   * Current balances derived from processed history events, one entry per bucket.
   *
   * @remarks
   * The backend fixes the timestamp to now and groups by account, so no arguments are sent. A
   * 404 means there is no history at all yet, which is a valid empty state rather than a failure.
   * Alongside `processingRequired`, the response reports `stale` when recent event edits have not
   * been folded into the derived balances yet.
   */
  async function fetchCurrentHistoricalBalances(): Promise<CurrentHistoricalBalancesResponse> {
    try {
      return CurrentHistoricalBalancesResponse.parse(await api.post('/balances/historical/current', {}));
    }
    catch (error: unknown) {
      if (isNotFound(error))
        return { entries: [], processingRequired: false, stale: false };
      throw error;
    }
  }

  /**
   * Every account's balance of every asset at `timestamp`, one entry per bucket.
   *
   * @remarks
   * Synchronous on purpose: the backend answers a date with no holdings with a 404, which only a
   * direct request can tell apart from a failure. Under an async task it would arrive as a failed
   * task with nothing but its message.
   *
   * @param timestamp - unix seconds
   * @param filters - narrows the buckets; none returns every account's
   */
  async function fetchHistoricalBalances(timestamp: number, filters: HistoricalBalanceFilters = {}): Promise<HistoricalBalancesResponse> {
    try {
      return HistoricalBalancesResponse.parse(await api.post('/balances/historical', { groupByAccount: true, timestamp, ...filters }));
    }
    catch (error: unknown) {
      if (isNotFound(error))
        return { entries: [], processingRequired: false };
      throw error;
    }
  }

  /**
   * One account's balance series of one asset, one series per location and protocol bucket.
   *
   * @remarks
   * Synchronous, unlike `fetchHistoricalBalanceSeries`, for the same reason as
   * `fetchHistoricalBalances`: a 404 means the account never held the asset in the range.
   */
  async function fetchBalanceSeries(payload: HistoricalBalanceSeriesPayload): Promise<HistoricalBalanceSeriesResponse> {
    try {
      return HistoricalBalanceSeriesResponse.parse(await api.post('/balances/historical/asset/series', payload));
    }
    catch (error: unknown) {
      if (isNotFound(error))
        return { entries: [], processingRequired: false };
      throw error;
    }
  }

  async function fetchHistoricalBalanceAssets(payload: HistoricalBalanceAssetsPayload): Promise<HistoricalBalanceAssetsResponse> {
    return HistoricalBalanceAssetsResponse.parse(await api.post('/balances/historical/assets', payload));
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
    fetchBalanceSeries,
    fetchCurrentHistoricalBalances,
    fetchHistoricalBalanceAssets,
    fetchHistoricalBalances,
    fetchHistoricalBalancesAtEvents,
    findHistoricalBalanceDivergence,
    fetchHistoricalBalanceSeries,
    processHistoricalBalances,
  };
}
