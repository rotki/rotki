import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RequestFailed } from '@/modules/core/api/request-result';
import { useReportOperations } from '@/modules/reports/use-report-operations';

const mockFetchReportsCaller = vi.fn();
const mockDeleteReportCaller = vi.fn();
const mockExportReportCSV = vi.fn();
const mockFetchActionableItems = vi.fn();
const mockFetchReportEventsCaller = vi.fn();

vi.mock('@/modules/reports/use-reports-api', () => ({
  useReportsApi: vi.fn(() => ({
    deleteReport: mockDeleteReportCaller,
    exportReportCSV: mockExportReportCSV,
    fetchActionableItems: mockFetchActionableItems,
    fetchReportEvents: mockFetchReportEventsCaller,
    fetchReports: mockFetchReportsCaller,
  })),
}));

const mockNotifyError = vi.fn();
const mockShowErrorMessage = vi.fn();
const mockShowSuccessMessage = vi.fn();

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: vi.fn((e: unknown): string => (e instanceof Error ? e.message : String(e))),
  useNotifications: vi.fn(() => ({
    notifyError: mockNotifyError,
    showErrorMessage: mockShowErrorMessage,
    showSuccessMessage: mockShowSuccessMessage,
  })),
}));

vi.mock('@/modules/accounts/address-book/use-ens-operations', () => ({
  useEnsOperations: vi.fn(() => ({
    fetchEnsNames: vi.fn(),
  })),
}));

describe('useReportOperations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('fetchReports', () => {
    it('should fetch and update reports state', async () => {
      const mockReports = { entries: [{ identifier: 1 }], entriesFound: 1, entriesLimit: 10 };
      mockFetchReportsCaller.mockResolvedValue(mockReports);

      const { fetchReports } = useReportOperations();
      await fetchReports();

      expect(mockFetchReportsCaller).toHaveBeenCalledOnce();
    });

    it('should notify on fetch error', async () => {
      mockFetchReportsCaller.mockRejectedValue(new Error('Network error'));

      const { fetchReports } = useReportOperations();
      await fetchReports();

      expect(mockNotifyError).toHaveBeenCalledOnce();
    });
  });

  describe('deleteReport', () => {
    it('should delete and refetch reports', async () => {
      mockDeleteReportCaller.mockResolvedValue(true);
      mockFetchReportsCaller.mockResolvedValue({ entries: [], entriesFound: 0, entriesLimit: 10 });

      const { deleteReport } = useReportOperations();
      await deleteReport(1);

      expect(mockDeleteReportCaller).toHaveBeenCalledWith(1);
      expect(mockFetchReportsCaller).toHaveBeenCalledOnce();
    });

    it('should notify on delete error', async () => {
      mockDeleteReportCaller.mockRejectedValue(new Error('Delete failed'));

      const { deleteReport } = useReportOperations();
      await deleteReport(1);

      expect(mockNotifyError).toHaveBeenCalledOnce();
    });
  });

  describe('createCsv', () => {
    it('should show success on successful export', async () => {
      mockExportReportCSV.mockResolvedValue(true);

      const { createCsv } = useReportOperations();
      await createCsv(1, '/tmp/output');

      expect(mockExportReportCSV).toHaveBeenCalledWith(1, '/tmp/output');
      expect(mockShowSuccessMessage).toHaveBeenCalledOnce();
    });

    it('should show error on failed export', async () => {
      mockExportReportCSV.mockResolvedValue(false);

      const { createCsv } = useReportOperations();
      await createCsv(1, '/tmp/output');

      expect(mockShowErrorMessage).toHaveBeenCalledOnce();
    });
  });

  describe('fetchReportEvents', () => {
    it('should fetch and return events', async () => {
      const mockResponse = {
        entries: [{ timestamp: 1000 }],
        entriesFound: 1,
        entriesLimit: 100,
        entriesTotal: 1,
      };
      mockFetchReportEventsCaller.mockResolvedValue(mockResponse);

      const { fetchReportEvents } = useReportOperations();
      const result = await fetchReportEvents({ limit: 10, offset: 0, reportId: 1 });

      expect(result).toStrictEqual(ok({ data: [{ timestamp: 1000 }], found: 1, limit: 100, total: 1 }));
      expect(mockFetchReportEventsCaller).toHaveBeenCalledWith({ limit: 10, offset: 0, reportId: 1 });
    });

    it('should carry the failure for the table to show, without notifying', async () => {
      const failure = new Error('Fetch failed');
      mockFetchReportEventsCaller.mockRejectedValue(failure);

      const { fetchReportEvents } = useReportOperations();
      const result = await fetchReportEvents({ limit: 10, offset: 0, reportId: 1 });

      expect(result).toStrictEqual(err(RequestFailed({ cause: failure, message: 'Fetch failed', path: undefined, status: undefined })));
      expect(mockNotifyError).not.toHaveBeenCalled();
    });
  });

  describe('getActionableItems', () => {
    it('should fetch and update actionable items', async () => {
      const mockItems = { missingAcquisitions: ['ETH'], missingPrices: [] };
      mockFetchActionableItems.mockResolvedValue(mockItems);

      const { getActionableItems } = useReportOperations();
      await getActionableItems();

      expect(mockFetchActionableItems).toHaveBeenCalledOnce();
    });
  });
});
