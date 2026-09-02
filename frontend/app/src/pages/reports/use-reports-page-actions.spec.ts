import { err, ok } from 'plainfp/result';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, shallowRef } from 'vue';
import { Cancelled, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useReportsPageActions } from './use-reports-page-actions';

const PERIOD = { end: 1_600_100_000, start: 1_600_000_000 };

const {
  downloadFileByTextContent,
  exportReportData,
  fetchReports,
  generateReport,
  importReportData,
  interopState,
  notify,
  openDirectory,
  showErrorMessage,
  showSuccessMessage,
  submitTask,
  unpin,
  uploadReportData,
} = vi.hoisted(() => ({
  downloadFileByTextContent: vi.fn(),
  exportReportData: vi.fn(async (): Promise<unknown> => ({ events: [] })),
  fetchReports: vi.fn(async (): Promise<void> => {}),
  generateReport: vi.fn(async (): Promise<number> => 1),
  importReportData: vi.fn(async (): Promise<boolean> => true),
  interopState: { appSession: false },
  notify: vi.fn(),
  openDirectory: vi.fn(async (): Promise<string | undefined> => '/tmp/out'),
  showErrorMessage: vi.fn(),
  showSuccessMessage: vi.fn(),
  submitTask: vi.fn(),
  unpin: vi.fn(),
  uploadReportData: vi.fn(async (): Promise<boolean> => true),
}));

vi.mock('@/modules/reports/use-report-generation', () => ({
  useReportGeneration: (): { exportReportData: typeof exportReportData; generateReport: typeof generateReport } => ({
    exportReportData,
    generateReport,
  }),
}));

vi.mock('@/modules/reports/use-report-operations', () => ({
  useReportOperations: (): { fetchReports: typeof fetchReports } => ({ fetchReports }),
}));

vi.mock('@/modules/reports/use-reports-api', () => ({
  useReportsApi: (): { importReportData: typeof importReportData; uploadReportData: typeof uploadReportData } => ({
    importReportData,
    uploadReportData,
  }),
}));

vi.mock('@/modules/shell/pinned/use-pinned-panel', () => ({
  usePinnedPanel: (): { unpin: typeof unpin } => ({ unpin }),
}));

vi.mock('@/modules/task-center/use-native-task', () => ({
  useNativeTask: (): { submitTask: typeof submitTask } => ({ submitTask }),
}));

vi.mock('@/modules/core/common/file/download', () => ({
  downloadFileByTextContent,
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: (error: unknown): string => error instanceof Error ? error.message : String(error),
  useNotifications: (): {
    notify: typeof notify;
    showErrorMessage: typeof showErrorMessage;
    showSuccessMessage: typeof showSuccessMessage;
  } => ({ notify, showErrorMessage, showSuccessMessage }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<string> => shallowRef('DD/MM/YYYY'),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): { appSession: boolean; openDirectory: typeof openDirectory } => ({
    appSession: interopState.appSession,
    openDirectory,
  }),
}));

describe('pages/reports/useReportsPageActions', () => {
  const onNavigateToReport = vi.fn();
  const getPath = vi.fn((): string | undefined => undefined);
  let reportDebugData: Ref<File | undefined>;

  function setup(): ReturnType<typeof useReportsPageActions> {
    return useReportsPageActions({ getPath, onNavigateToReport, reportDebugData });
  }

  beforeEach(() => {
    vi.clearAllMocks();
    interopState.appSession = false;
    reportDebugData = shallowRef<File | undefined>();
    generateReport.mockResolvedValue(1);
    exportReportData.mockResolvedValue({ events: [] });
    openDirectory.mockResolvedValue('/tmp/out');
    getPath.mockReturnValue(undefined);
    submitTask.mockResolvedValue(ok(true));
  });

  describe('generate', () => {
    it('should clear the pinned report card before generating', async () => {
      await setup().generate(PERIOD);

      expect(unpin).toHaveBeenCalledTimes(1);
      expect(unpin.mock.invocationCallOrder[0]).toBeLessThan(generateReport.mock.invocationCallOrder[0]);
    });

    it('should navigate to the new report and notify with a re-navigating action', async () => {
      generateReport.mockResolvedValue(77);

      await setup().generate(PERIOD);

      expect(onNavigateToReport).toHaveBeenCalledWith(77);
      expect(notify).toHaveBeenCalledTimes(1);

      // The notification's action must land on the same report, not merely on the reports list.
      onNavigateToReport.mockClear();
      notify.mock.calls[0][0].action.action();
      expect(onNavigateToReport).toHaveBeenCalledWith(77);
    });

    it('should neither navigate nor notify when no report was produced', async () => {
      generateReport.mockResolvedValue(0);

      await setup().generate(PERIOD);

      expect(onNavigateToReport).not.toHaveBeenCalled();
      expect(notify).not.toHaveBeenCalled();
    });
  });

  describe('exportData on the desktop app', () => {
    beforeEach(() => {
      interopState.appSession = true;
    });

    it('should abort without exporting when no directory is chosen', async () => {
      openDirectory.mockResolvedValue(undefined);

      await setup().exportData(PERIOD);

      expect(exportReportData).not.toHaveBeenCalled();
    });

    it('should pass the chosen directory and report success', async () => {
      await setup().exportData(PERIOD);

      expect(exportReportData).toHaveBeenCalledWith({
        directoryPath: '/tmp/out',
        fromTimestamp: PERIOD.start,
        toTimestamp: PERIOD.end,
      });
      expect(showSuccessMessage).toHaveBeenCalled();
      expect(downloadFileByTextContent).not.toHaveBeenCalled();
    });

    it('should report a failure when the backend declines the export', async () => {
      exportReportData.mockResolvedValue(false);

      await setup().exportData(PERIOD);

      expect(showErrorMessage).toHaveBeenCalled();
      expect(showSuccessMessage).not.toHaveBeenCalled();
    });
  });

  describe('exportData on the web', () => {
    it('should download the payload instead of asking for a directory', async () => {
      await setup().exportData(PERIOD);

      expect(openDirectory).not.toHaveBeenCalled();
      expect(exportReportData).toHaveBeenCalledWith({ fromTimestamp: PERIOD.start, toTimestamp: PERIOD.end });
      expect(downloadFileByTextContent).toHaveBeenCalledWith(
        JSON.stringify({ events: [] }, null, 2),
        'pnl_debug.json',
        'application/json',
      );
    });

    it('should surface a thrown error as a message rather than rejecting', async () => {
      exportReportData.mockRejectedValue(new Error('boom'));

      await expect(setup().exportData(PERIOD)).resolves.toBeUndefined();

      expect(showErrorMessage).toHaveBeenCalledWith(expect.anything(), 'boom');
    });
  });

  describe('importData', () => {
    const file = new File(['{}'], 'debug.json');

    it('should do nothing when no file is held', async () => {
      await setup().importData();

      expect(submitTask).not.toHaveBeenCalled();
    });

    it('should upload the file itself when there is no local path', async () => {
      set(reportDebugData, file);

      await setup().importData();

      const { run } = submitTask.mock.calls[0][0];
      await run({ runTask: async (fn: () => Promise<boolean>) => ok(await fn()) });

      expect(uploadReportData).toHaveBeenCalledWith(file);
      expect(importReportData).not.toHaveBeenCalled();
    });

    it('should import by path when the desktop app resolves one', async () => {
      set(reportDebugData, file);
      getPath.mockReturnValue('/home/user/debug.json');

      await setup().importData();

      const { run } = submitTask.mock.calls[0][0];
      await run({ runTask: async (fn: () => Promise<boolean>) => ok(await fn()) });

      expect(importReportData).toHaveBeenCalledWith('/home/user/debug.json');
      expect(uploadReportData).not.toHaveBeenCalled();
    });

    it('should refresh the reports on success', async () => {
      set(reportDebugData, file);

      await setup().importData();

      expect(showSuccessMessage).toHaveBeenCalled();
      expect(fetchReports).toHaveBeenCalledTimes(1);
    });

    it('should report a failure and not refresh when the import returns false', async () => {
      set(reportDebugData, file);
      submitTask.mockResolvedValue(ok(false));

      await setup().importData();

      expect(showErrorMessage).toHaveBeenCalled();
      expect(fetchReports).not.toHaveBeenCalled();
    });

    it('should refresh quietly on a cancellation, with no error shown', async () => {
      set(reportDebugData, file);
      submitTask.mockResolvedValue(err<TaskError>(Cancelled({ message: 'stopped' })));

      await setup().importData();

      expect(fetchReports).toHaveBeenCalledTimes(1);
      expect(showErrorMessage).not.toHaveBeenCalled();
    });

    it('should surface an actionable failure with its message', async () => {
      set(reportDebugData, file);
      submitTask.mockResolvedValue(err<TaskError>(TaskFailed({ message: 'bad json' })));

      await setup().importData();

      expect(showErrorMessage).toHaveBeenCalledWith(expect.anything(), expect.stringContaining('bad json'));
      expect(fetchReports).not.toHaveBeenCalled();
    });

    it('should lower the loading flag again once the import settles', async () => {
      set(reportDebugData, file);
      const { importData, importDataLoading } = setup();

      const pending = importData();
      expect(get(importDataLoading)).toBe(true);

      await pending;
      expect(get(importDataLoading)).toBe(false);
    });
  });
});
