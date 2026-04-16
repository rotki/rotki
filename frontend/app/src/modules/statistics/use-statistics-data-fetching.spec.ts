import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useStatisticsDataFetching } from './use-statistics-data-fetching';
import '@test/i18n';

const mockQueryNetValueData = vi.fn();
const mockNotifyError = vi.fn();

vi.mock('@/modules/statistics/api/use-statistics-api', () => ({
  useStatisticsApi: vi.fn(() => ({
    queryNetValueData: mockQueryNetValueData,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (error: unknown): string => (error instanceof Error ? error.message : String(error)),
  useNotifications: vi.fn(() => ({
    notifyError: mockNotifyError,
  })),
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
      expect(mockNotifyError).not.toHaveBeenCalled();
    });

    it('should notify on error without displaying', async () => {
      mockQueryNetValueData.mockRejectedValue(new Error('Network error'));

      const { fetchNetValue } = useStatisticsDataFetching();
      await fetchNetValue();

      expect(mockNotifyError).toHaveBeenCalledOnce();
      expect(mockNotifyError).toHaveBeenCalledWith(
        expect.any(String),
        expect.stringContaining('Network error'),
        { display: false },
      );
    });
  });
});
