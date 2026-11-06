import type { useInterop } from '@/modules/shell/app/use-electron-interop';
import { createMock } from '@test/utils/create-mock';
import { withSetup } from '@test/utils/with-setup';
import dayjs from 'dayjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { snapshotFileName, useSnapshotExport } from '@/modules/dashboard/snapshots/composables/use-snapshot-export';

const { downloadFileByBlob, downloadSnapshot, exportSnapshotCSV, interop, notifyError, notifyInfo, openDirectory } = vi.hoisted(() => ({
  downloadFileByBlob: vi.fn(),
  downloadSnapshot: vi.fn(),
  exportSnapshotCSV: vi.fn(),
  interop: { appSession: false },
  notifyError: vi.fn<(title: string, message: string) => void>(),
  notifyInfo: vi.fn<(title: string, message: string) => void>(),
  openDirectory: vi.fn(),
}));

vi.mock('@/modules/core/common/file/download', () => ({ downloadFileByBlob }));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): { notifyError: typeof notifyError; notifyInfo: typeof notifyInfo } => ({ notifyError, notifyInfo }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): ReturnType<typeof useInterop> =>
    createMock<ReturnType<typeof useInterop>>({ appSession: interop.appSession, openDirectory }),
}));

vi.mock('@/modules/settings/api/use-snapshot-api', () => ({
  useSnapshotApi: (): { downloadSnapshot: typeof downloadSnapshot; exportSnapshotCSV: typeof exportSnapshotCSV } => ({
    downloadSnapshot,
    exportSnapshotCSV,
  }),
}));

describe('modules/dashboard/snapshots/composables/use-snapshot-export', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    interop.appSession = false;
  });

  it('should name the file year, month, day, so downloads sort by date', () => {
    const timestamp = dayjs('2026-10-13T09:58:16').unix();

    expect(snapshotFileName(timestamp)).toBe('20261013095816-snapshot.zip');
  });

  it('should download the zip in the browser', async () => {
    const blob = new Blob(['zip']);
    downloadSnapshot.mockResolvedValue(blob);
    const { exportSnapshot } = withSetup(() => useSnapshotExport()).result;

    await expect(exportSnapshot(100)).resolves.toBe(true);

    expect(downloadSnapshot).toHaveBeenCalledWith(100);
    expect(downloadFileByBlob).toHaveBeenCalledWith(blob, snapshotFileName(100));
  });

  it('should report a failed download as a toast rather than rejecting', async () => {
    downloadSnapshot.mockRejectedValue(new Error('backend said no'));
    const { exporting, exportSnapshot } = withSetup(() => useSnapshotExport()).result;

    await expect(exportSnapshot(100)).resolves.toBe(false);

    expect(notifyError).toHaveBeenCalledWith(expect.any(String), 'backend said no');
    expect(get(exporting)).toBeUndefined();
  });

  it('should write CSV files to the directory picked in the app', async () => {
    interop.appSession = true;
    openDirectory.mockResolvedValue('/tmp/out');
    exportSnapshotCSV.mockResolvedValue(true);
    const { exportSnapshot } = withSetup(() => useSnapshotExport()).result;

    await expect(exportSnapshot(100)).resolves.toBe(true);

    expect(exportSnapshotCSV).toHaveBeenCalledWith({ path: '/tmp/out', timestamp: 100 });
    expect(notifyInfo).toHaveBeenCalledWith(expect.any(String), 'dashboard.snapshot.download.message.success');
  });

  it('should do nothing when the directory picker is cancelled', async () => {
    interop.appSession = true;
    openDirectory.mockResolvedValue(undefined);
    const { exportSnapshot } = withSetup(() => useSnapshotExport()).result;

    await expect(exportSnapshot(100)).resolves.toBe(false);

    expect(exportSnapshotCSV).not.toHaveBeenCalled();
    expect(notifyInfo).not.toHaveBeenCalled();
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should track the snapshot being exported, and ignore a second while it runs', async () => {
    let finish: (blob: Blob) => void = () => {};
    downloadSnapshot.mockReturnValue(new Promise<Blob>((resolve) => {
      finish = resolve;
    }));
    const { exporting, exportSnapshot } = withSetup(() => useSnapshotExport()).result;

    const first = exportSnapshot(100);
    expect(get(exporting)).toBe(100);
    await expect(exportSnapshot(200)).resolves.toBe(false);

    finish(new Blob(['zip']));
    await first;

    expect(downloadSnapshot).toHaveBeenCalledTimes(1);
    expect(get(exporting)).toBeUndefined();
  });
});
