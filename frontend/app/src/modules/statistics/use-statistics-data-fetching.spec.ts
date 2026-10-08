import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RequestCancelledError } from '@/modules/core/api/request-queue/errors';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';
import { useStatisticsDataFetching } from './use-statistics-data-fetching';
import '@test/i18n';

const mockQueryNetValueData = vi.fn();
const mockLoggerError = vi.fn();

vi.mock('@/modules/statistics/api/use-statistics-api', () => ({
  useStatisticsApi: vi.fn(() => ({
    queryNetValueData: mockQueryNetValueData,
  })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { error: (...args: unknown[]): void => mockLoggerError(...args) },
}));

describe('useStatisticsDataFetching', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('fetchNetValue', () => {
    it('should fetch net value data and update store', async () => {
      const mockData = { data: [1, 2], times: [100, 200] };
      mockQueryNetValueData.mockResolvedValue(mockData);

      const { fetchNetValue } = useStatisticsDataFetching();
      await fetchNetValue();

      expect(mockQueryNetValueData).toHaveBeenCalledOnce();
      expect(get(useStatisticsStore().netValueError)).toBeUndefined();
    });

    it('should record the reason on the store for the chart to show, and log it', async () => {
      const error = new Error('Network error');
      mockQueryNetValueData.mockRejectedValue(error);

      const { fetchNetValue } = useStatisticsDataFetching();
      await fetchNetValue();

      expect(get(useStatisticsStore().netValueError)).toBe('Network error');
      expect(mockLoggerError).toHaveBeenCalledWith(error);
    });

    it('should clear a previous reason once a read succeeds', async () => {
      mockQueryNetValueData.mockRejectedValue(new Error('Network error'));
      const { fetchNetValue } = useStatisticsDataFetching();
      await fetchNetValue();

      mockQueryNetValueData.mockResolvedValue({ data: [1], times: [100] });
      await fetchNetValue();

      expect(get(useStatisticsStore().netValueError)).toBeUndefined();
    });

    it('should leave the reason alone when the request was cancelled', async () => {
      mockQueryNetValueData.mockRejectedValue(new RequestCancelledError('cancelled'));

      const { fetchNetValue } = useStatisticsDataFetching();
      await fetchNetValue();

      expect(get(useStatisticsStore().netValueError)).toBeUndefined();
      expect(mockLoggerError).not.toHaveBeenCalled();
    });
  });
});
