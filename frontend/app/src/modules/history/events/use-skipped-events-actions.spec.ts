import { flushPromises } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { useSkippedEventsActions } from './use-skipped-events-actions';

const {
  appSession,
  downloadSkippedEventsCSV,
  exportSkippedEventsCSV,
  getSkippedEventsSummary,
  openDirectory,
  reProcessSkippedEvents,
  setMessage,
} = vi.hoisted(() => ({
  appSession: { value: true },
  downloadSkippedEventsCSV: vi.fn(),
  exportSkippedEventsCSV: vi.fn(),
  getSkippedEventsSummary: vi.fn(),
  openDirectory: vi.fn(),
  reProcessSkippedEvents: vi.fn(),
  setMessage: vi.fn(),
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

vi.mock('@/modules/core/common/use-message-store', () => ({
  useMessageStore: (): Record<string, unknown> => ({ setMessage }),
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
      expect(setMessage).not.toHaveBeenCalled();
    });

    it('should report a successful write', async () => {
      const { exportCSV } = await actions();

      await exportCSV();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ success: true }));
    });

    it('should report a write the backend refused', async () => {
      exportSkippedEventsCSV.mockResolvedValue(false);
      const { exportCSV } = await actions();

      await exportCSV();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        description: 'actions.online_events.skipped.csv_export.message.failure',
        success: false,
      }));
    });

    it('should report a write that threw', async () => {
      exportSkippedEventsCSV.mockRejectedValue(new Error('disk full'));
      const { exportCSV } = await actions();

      await exportCSV();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        description: 'disk full',
        success: false,
      }));
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

      expect(setMessage).not.toHaveBeenCalled();
    });

    it('should surface the reason a download failed', async () => {
      downloadSkippedEventsCSV.mockResolvedValue({ message: 'no events', success: false });
      const { exportCSV } = await actions();

      await exportCSV();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        description: 'no events',
        success: false,
      }));
    });

    it('should fall back to a generic reason when the failure names none', async () => {
      downloadSkippedEventsCSV.mockResolvedValue({ success: false });
      const { exportCSV } = await actions();

      await exportCSV();

      expect(setMessage).toHaveBeenCalledWith(expect.objectContaining({
        description: 'transactions.events.skipped.download_failed',
      }));
    });

    it('should report a download that threw', async () => {
      downloadSkippedEventsCSV.mockRejectedValue(new Error('offline'));
      const { exportCSV } = await actions();

      await exportCSV();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        description: 'offline',
        success: false,
      }));
    });
  });

  describe('reprocessing', () => {
    it('should report success when every skipped event was decoded', async () => {
      const { reProcessSkippedEvents: reProcess } = await actions();

      await reProcess();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        description: 'transactions.events.skipped.reprocess.success.all',
        success: true,
      }));
    });

    it('should still count a partial run as a success', async () => {
      reProcessSkippedEvents.mockResolvedValue({ successful: 1, total: 3 });
      const { reProcessSkippedEvents: reProcess } = await actions();

      await reProcess();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        description: 'transactions.events.skipped.reprocess.success.some::1, 3',
        success: true,
      }));
    });

    it('should report a failure when nothing could be decoded', async () => {
      reProcessSkippedEvents.mockResolvedValue({ successful: 0, total: 3 });
      const { reProcessSkippedEvents: reProcess } = await actions();

      await reProcess();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        description: 'transactions.events.skipped.reprocess.failed.no_processed_events',
        success: false,
      }));
    });

    it('should report a run that threw', async () => {
      reProcessSkippedEvents.mockRejectedValue(new Error('decoder crashed'));
      const { reProcessSkippedEvents: reProcess } = await actions();

      await reProcess();

      expect(setMessage).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({
        description: 'decoder crashed',
        success: false,
      }));
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
