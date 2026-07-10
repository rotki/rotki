import type { WrapStatisticsResult } from '@/modules/statistics/api/use-wrap-statistics-api';
import { bigNumberify } from '@rotki/common';
import { flushPromises } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useWrappedStatistics } from '@/modules/statistics/wrapped/use-wrapped-statistics';

const mockFetchWrapStatistics = vi.fn();
const mockLoggerError = vi.hoisted(() => vi.fn());

vi.mock('@/modules/statistics/api/use-wrap-statistics-api', () => ({
  useWrapStatisticsApi: (): { fetchWrapStatistics: typeof mockFetchWrapStatistics } => ({
    fetchWrapStatistics: mockFetchWrapStatistics,
  }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { error: mockLoggerError },
}));

function statistics(): WrapStatisticsResult {
  return {
    ethOnGas: bigNumberify(1),
    ethOnGasPerAddress: {},
    gnosisMaxPaymentsByCurrency: [],
    score: 5,
    topDaysByNumberOfTransactions: [],
    tradesByExchange: {},
    transactionsPerChain: {},
    transactionsPerProtocol: [],
  };
}

describe('useWrappedStatistics', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should fetch statistics with the current range and store the summary', async () => {
    const result = statistics();
    mockFetchWrapStatistics.mockResolvedValue(result);
    const { fetchData, loading, summary } = useWrappedStatistics(ref(100), ref(200), ref(false));

    await fetchData();

    expect(mockFetchWrapStatistics).toHaveBeenCalledWith({ end: 200, start: 100 });
    expect(get(summary)).toStrictEqual(result);
    expect(get(loading)).toBe(false);
  });

  it('should set the summary to null and log when the request fails', async () => {
    const error = new Error('boom');
    mockFetchWrapStatistics.mockRejectedValue(error);
    const { fetchData, summary } = useWrappedStatistics(ref(0), ref(0), ref(false));

    await fetchData();

    expect(get(summary)).toBeNull();
    expect(mockLoggerError).toHaveBeenCalledWith(error);
  });

  it('should skip fetching when a request is already in progress', async () => {
    let resolveFetch: (value: WrapStatisticsResult) => void = () => {};
    mockFetchWrapStatistics.mockReturnValue(new Promise<WrapStatisticsResult>((resolve) => {
      resolveFetch = resolve;
    }));
    const { fetchData } = useWrappedStatistics(ref(0), ref(0), ref(false));

    const first = fetchData();
    await fetchData();
    expect(mockFetchWrapStatistics).toHaveBeenCalledTimes(1);

    resolveFetch(statistics());
    await first;
  });

  it('should refetch when refreshing transitions from true to false', async () => {
    mockFetchWrapStatistics.mockResolvedValue(statistics());
    const refreshing = ref<boolean>(true);
    useWrappedStatistics(ref(0), ref(0), refreshing);

    set(refreshing, false);
    await flushPromises();

    expect(mockFetchWrapStatistics).toHaveBeenCalledTimes(1);
  });

  it('should not refetch when refreshing transitions from false to true', async () => {
    mockFetchWrapStatistics.mockResolvedValue(statistics());
    const refreshing = ref<boolean>(false);
    useWrappedStatistics(ref(0), ref(0), refreshing);

    set(refreshing, true);
    await flushPromises();

    expect(mockFetchWrapStatistics).not.toHaveBeenCalled();
  });
});
