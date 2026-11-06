import type { ComputedRef, Ref } from 'vue';
import type { SkippedHistoryEventsSummary } from '@/modules/history/events/event-payloads';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSkippedHistoryEventsApi } from '@/modules/history/api/events/use-skipped-history-events-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

/** One row of the summary: how many events were skipped at a given location. */
export interface SkippedEventsLocation {
  location: string;
  number: number;
}

interface UseSkippedEventsActionsReturn {
  /**
   * Writes the skipped events to a CSV.
   *
   * @remarks
   * In the desktop app this asks for a directory and writes there; on the web it downloads instead,
   * since there is no filesystem to write to.
   */
  exportCSV: () => Promise<void>;
  /** True while the skipped events are being reprocessed. */
  loading: Readonly<Ref<boolean>>;
  /** The per-location counts, as table rows. */
  locationsData: ComputedRef<SkippedEventsLocation[]>;
  /** Asks the backend to decode the skipped events again, then refreshes the summary. */
  reProcessSkippedEvents: () => Promise<void>;
  /** Why the last reprocess failed, or processed nothing; cleared when the next one starts. */
  reprocessFailure: Readonly<Ref<unknown>>;
  /** Says how many were processed when a reprocess left some behind; cleared when the next one starts. */
  reprocessNote: Readonly<Ref<string | undefined>>;
  /** The counts behind the table, refreshed after a reprocess. */
  skippedEvents: Ref<SkippedHistoryEventsSummary>;
}

/**
 * Drives the skipped-events settings row: the summary it shows and the two actions on it.
 *
 * @returns the summary and the actions. An export reports its outcome as a toast; a reprocess keeps a
 * failure, or a partial count, for the row to show, a full success showing as the counts dropping.
 */
export function useSkippedEventsActions(): UseSkippedEventsActionsReturn {
  const loading = shallowRef<boolean>(false);
  const reprocessFailure = shallowRef<unknown>();
  const reprocessNote = shallowRef<string>();

  const { t } = useI18n({ useScope: 'global' });
  const { notifyError, notifyInfo } = useNotifications();
  const { appSession, openDirectory } = useInterop();
  const {
    downloadSkippedEventsCSV,
    exportSkippedEventsCSV,
    getSkippedEventsSummary,
    reProcessSkippedEvents: reProcessSkippedEventsCaller,
  } = useSkippedHistoryEventsApi();

  const { execute: refreshSkippedEvents, state: skippedEvents } = useAsyncState<SkippedHistoryEventsSummary>(
    getSkippedEventsSummary,
    {
      locations: {},
      total: 0,
    },
    {
      delay: 0,
      immediate: true,
      resetOnExecute: false,
    },
  );

  const locationsData = computed<SkippedEventsLocation[]>(() =>
    Object.entries(get(skippedEvents).locations).map(([location, number]) => ({
      location,
      number,
    })),
  );

  function showExportCSVError(description: string): void {
    notifyError(t('transactions.events.skipped.csv_export_error'), description);
  }

  async function createCsv(path: string): Promise<void> {
    const title = t('actions.online_events.skipped.csv_export.title');
    try {
      if (await exportSkippedEventsCSV(path))
        notifyInfo(title, t('actions.online_events.skipped.csv_export.message.success'));
      else
        notifyError(title, t('actions.online_events.skipped.csv_export.message.failure'));
    }
    catch (error: unknown) {
      notifyError(title, getErrorMessage(error));
    }
  }

  async function exportCSV(): Promise<void> {
    try {
      if (appSession) {
        const directory = await openDirectory(t('common.select_directory'));
        if (!directory)
          return;

        await createCsv(directory);
      }
      else {
        const result = await downloadSkippedEventsCSV();
        if (!result.success)
          showExportCSVError(result.message ?? t('transactions.events.skipped.download_failed'));
      }
    }
    catch (error: unknown) {
      showExportCSVError(getErrorMessage(error));
    }
  }

  async function reProcessSkippedEvents(): Promise<void> {
    set(loading, true);
    set(reprocessFailure, undefined);
    set(reprocessNote, undefined);
    try {
      const { successful, total } = await reProcessSkippedEventsCaller();
      if (successful === 0)
        set(reprocessFailure, t('transactions.events.skipped.reprocess.failed.no_processed_events'));
      else if (successful < total)
        set(reprocessNote, t('transactions.events.skipped.reprocess.success.some', { successful, total }));
    }
    catch (error: unknown) {
      logger.error(error);
      set(reprocessFailure, error);
    }
    finally {
      set(loading, false);
    }

    await refreshSkippedEvents();
  }

  return {
    exportCSV,
    loading: readonly(loading),
    locationsData,
    reProcessSkippedEvents,
    reprocessFailure: shallowReadonly(reprocessFailure),
    reprocessNote: readonly(reprocessNote),
    skippedEvents,
  };
}
