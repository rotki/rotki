import type { TaskResult } from '@/modules/core/tasks/use-task-handler';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useReportGeneration } from '@/modules/reports/use-report-generation';

const mockGenerateReportCaller = vi.fn();
const mockExportReportDataCaller = vi.fn();

vi.mock('@/modules/reports/use-reports-api', () => ({
  useReportsApi: vi.fn(() => ({
    exportReportData: mockExportReportDataCaller,
    generateReport: mockGenerateReportCaller,
  })),
}));

const mockGetProgress = vi.fn();

vi.mock('@/modules/history/api/use-history-api', () => ({
  useHistoryApi: vi.fn(() => ({
    getProgress: mockGetProgress,
  })),
}));

const mockFetchReports = vi.fn();

vi.mock('@/modules/reports/use-report-operations', () => ({
  useReportOperations: vi.fn(() => ({
    fetchReports: mockFetchReports,
  })),
}));

const mockRunTask = vi.fn();

vi.mock('@/modules/core/tasks/use-task-handler', () => ({
  isActionableFailure: vi.fn((outcome: TaskResult<unknown>): boolean =>
    !outcome.success && !('cancelled' in outcome && outcome.cancelled) && !('skipped' in outcome && outcome.skipped),
  ),
  useTaskHandler: vi.fn(() => ({
    runTask: mockRunTask,
  })),
}));

describe('useReportGeneration', () => {
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  describe('generateReport', () => {
    it('should generate report and fetch reports on success', async () => {
      mockRunTask.mockResolvedValue({
        result: 42,
        success: true,
      });
      mockFetchReports.mockResolvedValue(undefined);

      const { generateReport } = scope.run(() => useReportGeneration())!;
      const result = await generateReport({ end: 2000, start: 1000 });

      expect(result).toBe(42);
      expect(mockRunTask).toHaveBeenCalledOnce();
      expect(mockFetchReports).toHaveBeenCalledOnce();
    });

    it('should return -1 on actionable failure', async () => {
      mockRunTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: false,
        error: new Error('Failed'),
        message: 'Generation failed',
        skipped: false,
        success: false,
      });

      const { generateReport } = scope.run(() => useReportGeneration())!;
      const result = await generateReport({ end: 2000, start: 1000 });

      expect(result).toBe(-1);
      expect(mockFetchReports).not.toHaveBeenCalled();
    });

    it('should set report error on zero result', async () => {
      mockRunTask.mockResolvedValue({
        result: 0,
        success: true,
      });

      const { generateReport } = scope.run(() => useReportGeneration())!;
      const result = await generateReport({ end: 2000, start: 1000 });

      expect(result).toBe(0);
      expect(mockFetchReports).not.toHaveBeenCalled();
    });
  });

  describe('exportReportData', () => {
    it('should export report data on success', async () => {
      const mockData = { someData: true };
      mockRunTask.mockResolvedValue({
        result: mockData,
        success: true,
      });

      const { exportReportData } = scope.run(() => useReportGeneration())!;
      const result = await exportReportData({ fromTimestamp: 1000, toTimestamp: 2000 });

      expect(result).toEqual(mockData);
    });

    it('should return empty object on failure', async () => {
      mockRunTask.mockResolvedValue({
        backendCancelled: false,
        cancelled: false,
        error: new Error('Export failed'),
        message: 'Export failed',
        skipped: false,
        success: false,
      });

      const { exportReportData } = scope.run(() => useReportGeneration())!;
      const result = await exportReportData({ fromTimestamp: 1000, toTimestamp: 2000 });

      expect(result).toEqual({});
    });
  });
});
