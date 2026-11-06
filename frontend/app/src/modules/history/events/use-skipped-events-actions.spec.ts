import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { useSkippedEventsActions } from './use-skipped-events-actions';

const {
  appSession,
  downloadSkippedEventsCSV,
  exportSkippedEventsCSV,
  getSkippedEventsSummary,
  notifyError,
  notifyInfo,
  openDirectory,
  reProcessSkippedEvents,
} = vi.hoisted(() => ({
  appSession: { value: true },
  downloadSkippedEventsCSV: vi.fn(),
  exportSkippedEventsCSV: vi.fn(),
  getSkippedEventsSummary: vi.fn(),
  notifyError: vi.fn<(title: string, message: string) => void>(),
  notifyInfo: vi.fn<(title: string, message: string) => void>(),
  openDirectory: vi.fn(),
  reProcessSkippedEvents: vi.fn(),
}));

vi.mock('@/modules/history/api/events/use-skipped-history-events-api', () => ({
  useSkippedHistoryEventsApi: (): Record<string, unknown> => ({
    downloadSkippedEventsCSV,
    exportSkippedEventsCSV,
    getSkippedEventsSummary,
    reProcessSkippedEvents,
  }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): Record<string, unknown> => ({
    get appSession(): boolean {
      return appSession.value;
    },
    openDirectory,
  }),
}));

vi.mock('@/modules/core/notifications/use-notifications', async () => ({
  getErrorMessage: (await vi.importActual<typeof import('@/modules/core/common/logging/error-handling')>(
    '@/modules/core/common/logging/error-handling',
  )).getErrorMessage,
  useNotifications: (): Record<string, unknown> => ({ notifyError, notifyInfo }),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  getDefaultLogLevel: vi.fn(() => 'debug'),
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
  setLevel: vi.fn(),
}));

let scope: ReturnType<typeof effectScope>;

async function actions(): Promise<ReturnType<typeof useSkippedEventsActions>> {
  scope = effectScope();
  const api = scope.run(() => useSkippedEventsActions())!;
  await flushPromises();
  return api;
}

describe('modules/history/events/useSkippedEventsActions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    appSession.value = true;
    getSkippedEventsSummary.mockResolvedValue({ locations: { kraken: 2 }, total: 2 });
    exportSkippedEventsCSV.mockResolvedValue(true);
    downloadSkippedEventsCSV.mockResolvedValue({ success: true });
    openDirectory.mockResolvedValue('/tmp/exports');
    reProcessSkippedEvents.mockResolvedValue({ successful: 2, total: 2 });
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the summary', () => {
    it('should read it as soon as the row is shown', async () => {
      const { skippedEvents } = await actions();

      expect(getSkippedEventsSummary).toHaveBeenCalledOnce();
      expect(get(skippedEvents).total).toBe(2);
    });

    it('should turn the per-location counts into rows', async () => {
      getSkippedEventsSummary.mockResolvedValue({ locations: { binance: 1, kraken: 3 }, total: 4 });

      const { locationsData } = await actions();

      expect(get(locationsData)).toEqual([
        { location: 'binance', number: 1 },
        { location: 'kraken', number: 3 },
      ]);
    });

    it('should have no rows when nothing was skipped', async () => {
      getSkippedEventsSummary.mockResolvedValue({ locations: {}, total: 0 });

      const { locationsData } = await actions();

      expect(get(locationsData)).toEqual([]);
    });
  });

  describe('exporting from the desktop app', () => {
    it('should write to the directory the user picked', async () => {
      const { exportCSV } = await actions();

      await exportCSV();

      expect(openDirectory).toHaveBeenCalledOnce();
      expect(exportSkippedEventsCSV).toHaveBeenCalledExactlyOnceWith('/tmp/exports');
      expect(downloadSkippedEventsCSV).not.toHaveBeenCalled();
    });

    it('should write nothing when the user picked no directory', async () => {
      openDirectory.mockResolvedValue(undefined);
      const { exportCSV } = await actions();

      await exportCSV();

      expect(exportSkippedEventsCSV).not.toHaveBeenCalled();
      expect(notifyInfo).not.toHaveBeenCalled();
      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should report a successful write', async () => {
      const { exportCSV } = await actions();

      await exportCSV();

      expect(notifyInfo).toHaveBeenCalledExactlyOnceWith(
        'actions.online_events.skipped.csv_export.title',
        'actions.online_events.skipped.csv_export.message.success',
      );
    });

    it('should report a write the backend refused', async () => {
      exportSkippedEventsCSV.mockResolvedValue(false);
      const { exportCSV } = await actions();

      await exportCSV();

      expect(notifyError).toHaveBeenCalledExactlyOnceWith(expect.any(String), 'actions.online_events.skipped.csv_export.message.failure');
    });

    it('should report a write that threw', async () => {
      exportSkippedEventsCSV.mockRejectedValue(new Error('disk full'));
      const { exportCSV } = await actions();

      await exportCSV();

      expect(notifyError).toHaveBeenCalledExactlyOnceWith(expect.any(String), 'disk full');
    });
  });

  describe('exporting from the browser', () => {
    beforeEach(() => {
      appSession.value = false;
    });

    it('should download rather than ask for a directory there is none of', async () => {
      const { exportCSV } = await actions();

      await exportCSV();

      expect(downloadSkippedEventsCSV).toHaveBeenCalledOnce();
      expect(openDirectory).not.toHaveBeenCalled();
      expect(exportSkippedEventsCSV).not.toHaveBeenCalled();
    });

    it('should stay quiet when the download worked, since the browser shows it', async () => {
      const { exportCSV } = await actions();

      await exportCSV();

      expect(notifyInfo).not.toHaveBeenCalled();
      expect(notifyError).not.toHaveBeenCalled();
    });

    it('should surface the reason a download failed', async () => {
      downloadSkippedEventsCSV.mockResolvedValue({ message: 'no events', success: false });
      const { exportCSV } = await actions();

      await exportCSV();

      expect(notifyError).toHaveBeenCalledExactlyOnceWith(expect.any(String), 'no events');
    });

    it('should fall back to a generic reason when the failure names none', async () => {
      downloadSkippedEventsCSV.mockResolvedValue({ success: false });
      const { exportCSV } = await actions();

      await exportCSV();

      expect(notifyError).toHaveBeenCalledWith(expect.any(String), 'transactions.events.skipped.download_failed');
    });

    it('should report a download that threw', async () => {
      downloadSkippedEventsCSV.mockRejectedValue(new Error('offline'));
      const { exportCSV } = await actions();

      await exportCSV();

      expect(notifyError).toHaveBeenCalledExactlyOnceWith(expect.any(String), 'offline');
    });
  });

  describe('reprocessing', () => {
    it('should name nothing when every skipped event was decoded, the counts dropping saying so', async () => {
      const { reProcessSkippedEvents: reProcess, reprocessFailure, reprocessNote } = await actions();

      await reProcess();

      expect(get(reprocessFailure)).toBeUndefined();
      expect(get(reprocessNote)).toBeUndefined();
    });

    it('should keep a partial run as a note on the row, not a failure', async () => {
      reProcessSkippedEvents.mockResolvedValue({ successful: 1, total: 3 });
      const { reProcessSkippedEvents: reProcess, reprocessFailure, reprocessNote } = await actions();

      await reProcess();

      expect(get(reprocessNote)).toBe('transactions.events.skipped.reprocess.success.some::1, 3');
      expect(get(reprocessFailure)).toBeUndefined();
    });

    it('should keep a failure when nothing could be decoded', async () => {
      reProcessSkippedEvents.mockResolvedValue({ successful: 0, total: 3 });
      const { reProcessSkippedEvents: reProcess, reprocessFailure } = await actions();

      await reProcess();

      expect(get(reprocessFailure)).toEqual({
        failure: 'transactions.events.skipped.reprocess.failed.no_processed_events',
        title: 'transactions.events.skipped.reprocess.failed.title',
      });
    });

    it('should keep a run that threw as the failure', async () => {
      const error = new Error('decoder crashed');
      reProcessSkippedEvents.mockRejectedValue(error);
      const { reProcessSkippedEvents: reProcess, reprocessFailure } = await actions();

      await reProcess();

      expect(get(reprocessFailure)).toEqual({ failure: error, title: 'transactions.events.skipped.reprocess.failed.title' });
    });

    it('should drop the last failure and note when the next run starts', async () => {
      reProcessSkippedEvents.mockResolvedValueOnce({ successful: 1, total: 3 });
      reProcessSkippedEvents.mockRejectedValueOnce(new Error('decoder crashed'));
      const { reProcessSkippedEvents: reProcess, reprocessFailure, reprocessNote } = await actions();

      await reProcess();
      await reProcess();
      expect(get(reprocessNote)).toBeUndefined();

      await reProcess();
      expect(get(reprocessFailure)).toBeUndefined();
    });

    it('should re-read the summary, since the counts have changed', async () => {
      const { reProcessSkippedEvents: reProcess } = await actions();
      getSkippedEventsSummary.mockClear();
      getSkippedEventsSummary.mockResolvedValue({ locations: {}, total: 0 });

      await reProcess();

      expect(getSkippedEventsSummary).toHaveBeenCalledOnce();
    });

    it('should re-read the summary even when the run failed', async () => {
      reProcessSkippedEvents.mockRejectedValue(new Error('decoder crashed'));
      const { reProcessSkippedEvents: reProcess } = await actions();
      getSkippedEventsSummary.mockClear();

      await reProcess();

      expect(getSkippedEventsSummary).toHaveBeenCalledOnce();
    });

    it('should stop showing progress once it is done', async () => {
      const { loading, reProcessSkippedEvents: reProcess } = await actions();

      await reProcess();

      expect(get(loading)).toBe(false);
    });

    it('should stop showing progress when the run threw', async () => {
      reProcessSkippedEvents.mockRejectedValue(new Error('decoder crashed'));
      const { loading, reProcessSkippedEvents: reProcess } = await actions();

      await reProcess();

      expect(get(loading)).toBe(false);
    });
  });
});
