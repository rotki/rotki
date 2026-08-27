import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';
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

vi.mock('@/modules/core/tasks/use-task-handler', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useTaskHandler: vi.fn(() => ({
      runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => {
        await taskFn();
        return mockRunTask(taskFn, ...rest);
      },
    })),
  };
});

describe('useReportGeneration', () => {
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    vi.clearAllMocks();
    vi.useFakeTimers();
    mockGenerateReportCaller.mockResolvedValue({ taskId: 1 });
    mockExportReportDataCaller.mockResolvedValue({ taskId: 2 });
  });

  afterEach(() => {
    scope.stop();
    vi.useRealTimers();
  });

  describe('generateReport', () => {
    it('should generate report and fetch reports on success', async () => {
      mockRunTask.mockResolvedValue(ok(42));
      mockFetchReports.mockResolvedValue(undefined);

      const { generateReport } = scope.run(() => useReportGeneration())!;
      const result = await generateReport({ end: 2000, start: 1000 });

      expect(result).toBe(42);
      expect(mockRunTask).toHaveBeenCalledOnce();
      expect(mockFetchReports).toHaveBeenCalledOnce();
    });

    it('should return -1 on actionable failure', async () => {
      mockRunTask.mockResolvedValue(err(TaskFailed({ cause: new Error('Failed'), message: 'Generation failed' })));

      const { generateReport } = scope.run(() => useReportGeneration())!;
      const result = await generateReport({ end: 2000, start: 1000 });

      expect(result).toBe(-1);
      expect(mockFetchReports).not.toHaveBeenCalled();
    });

    it('should set report error on zero result', async () => {
      mockRunTask.mockResolvedValue(ok(0));

      const { generateReport } = scope.run(() => useReportGeneration())!;
      const result = await generateReport({ end: 2000, start: 1000 });

      expect(result).toBe(0);
      expect(mockFetchReports).not.toHaveBeenCalled();
    });
  });

  describe('exportReportData', () => {
    it('should export report data on success', async () => {
      const mockData = { someData: true };
      mockRunTask.mockResolvedValue(ok(mockData));

      const { exportReportData } = scope.run(() => useReportGeneration())!;
      const result = await exportReportData({ fromTimestamp: 1000, toTimestamp: 2000 });

      expect(result).toEqual(mockData);
    });

    it('should return empty object on failure', async () => {
      mockRunTask.mockResolvedValue(err(TaskFailed({ cause: new Error('Export failed'), message: 'Export failed' })));

      const { exportReportData } = scope.run(() => useReportGeneration())!;
      const result = await exportReportData({ fromTimestamp: 1000, toTimestamp: 2000 });

      expect(result).toEqual({});
    });
  });
});
