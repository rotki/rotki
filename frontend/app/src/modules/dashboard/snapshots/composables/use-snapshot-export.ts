import type { Ref } from 'vue';
import dayjs from 'dayjs';
import { downloadFileByBlob } from '@/modules/core/common/file/download';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useSnapshotApi } from '@/modules/settings/api/use-snapshot-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface UseSnapshotExportReturn {
  /** The snapshot being exported, by timestamp, or undefined while none is. */
  exporting: Readonly<Ref<number | undefined>>;
  /** Exports one snapshot; resolves true once it is saved, false when cancelled or failed. */
  exportSnapshot: (timestamp: number) => Promise<boolean>;
}

/** The file name a downloaded snapshot gets: its time, year first, so the files sort by date. */
export function snapshotFileName(timestamp: number): string {
  return `${dayjs(timestamp * 1000).format('YYYYMMDDHHmmss')}-snapshot.zip`;
}

/**
 * Exports a balance snapshot: the desktop app writes CSV files to a directory the user picks, the
 * browser downloads a zip. Failures and the desktop result are reported as a message.
 */
export function useSnapshotExport(): UseSnapshotExportReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { setMessage } = useMessageStore();
  const { downloadSnapshot, exportSnapshotCSV } = useSnapshotApi();
  const { appSession, openDirectory } = useInterop();

  const exporting = shallowRef<number>();

  function report(description: string, success: boolean): void {
    setMessage({ description, success, title: t('dashboard.snapshot.download.message.title') });
  }

  async function exportToDirectory(timestamp: number): Promise<boolean> {
    const path = await openDirectory(t('common.select_directory'));
    if (!path)
      return false;

    const success = await exportSnapshotCSV({ path, timestamp });
    report(success ? t('dashboard.snapshot.download.message.success') : t('dashboard.snapshot.download.message.failure'), success);
    return success;
  }

  async function exportSnapshot(timestamp: number): Promise<boolean> {
    if (isDefined(exporting))
      return false;

    set(exporting, timestamp);
    try {
      if (appSession)
        return await exportToDirectory(timestamp);

      downloadFileByBlob(await downloadSnapshot(timestamp), snapshotFileName(timestamp));
      return true;
    }
    catch (error: unknown) {
      report(getErrorMessage(error), false);
      return false;
    }
    finally {
      set(exporting, undefined);
    }
  }

  return {
    exporting: readonly(exporting),
    exportSnapshot,
  };
}
