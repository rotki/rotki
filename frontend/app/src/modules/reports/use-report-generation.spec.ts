import { err, ok } from 'plainfp/result';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';
import { useReportGeneration } from '@/modules/reports/use-report-generation';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

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

// Native producer path: useNativeTask + the real orchestrator drive submitTask; only the task
// handler the facade delegates to is mocked, so runTask resolves from mockRunTask.
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
    // Both api calls return a pending task; the activity records its id so a cancel can abort it.
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

    it('should leave no progress poll behind when a second generation joins the running one', async () => {
      let finish: (value: unknown) => void = () => {};
      mockRunTask.mockReturnValue(new Promise((resolve) => {
        finish = resolve;
      }));
      mockGetProgress.mockResolvedValue({ processingState: '', totalProgress: '50' });
      mockFetchReports.mockResolvedValue(undefined);

      const { generateReport } = scope.run(() => useReportGeneration())!;
      const first = generateReport({ end: 2000, start: 1000 });
      const second = generateReport({ end: 2000, start: 1000 });
      await vi.advanceTimersByTimeAsync(0);

      finish(ok(42));
      await Promise.all([first, second]);
      mockGetProgress.mockClear();

      await vi.advanceTimersByTimeAsync(10_000);

      expect(mockGetProgress).not.toHaveBeenCalled();
    });

    it('should poll progress while a generation runs', async () => {
      let finish: (value: unknown) => void = () => {};
      mockRunTask.mockReturnValue(new Promise((resolve) => {
        finish = resolve;
      }));
      mockGetProgress.mockResolvedValue({ processingState: '', totalProgress: '50' });
      mockFetchReports.mockResolvedValue(undefined);

      const { generateReport } = scope.run(() => useReportGeneration())!;
      const generation = generateReport({ end: 2000, start: 1000 });
      await vi.advanceTimersByTimeAsync(4_000);

      expect(mockGetProgress).toHaveBeenCalledTimes(2);

      finish(ok(42));
      await generation;
    });

    it('should poll progress when the task centre re-runs a generation', async () => {
      mockRunTask.mockResolvedValueOnce(err(TaskFailed({ cause: new Error('Failed'), message: 'Generation failed' })));
      mockGetProgress.mockResolvedValue({ processingState: '', totalProgress: '50' });
      mockFetchReports.mockResolvedValue(undefined);

      const { generateReport } = scope.run(() => useReportGeneration())!;
      await generateReport({ end: 2000, start: 1000 });
      await vi.advanceTimersByTimeAsync(0);

      let finish: (value: unknown) => void = () => {};
      mockRunTask.mockReturnValue(new Promise((resolve) => {
        finish = resolve;
      }));
      mockGetProgress.mockClear();

      const rerun = useTaskOrchestrator().rerun(makeActivityId(ActivityKind.PNL_REPORT));
      assert(rerun.ok);
      await vi.advanceTimersByTimeAsync(4_000);

      expect(mockGetProgress).toHaveBeenCalledTimes(2);

      finish(ok(42));
      await vi.advanceTimersByTimeAsync(0);
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
