import type { Message } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { SkippedHistoryEventsSummary } from '@/modules/history/events/event-payloads';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useMessageStore } from '@/modules/core/common/use-message-store';
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
  /** The counts behind the table, refreshed after a reprocess. */
  skippedEvents: Ref<SkippedHistoryEventsSummary>;
}

/**
 * Drives the skipped-events settings row: the summary it shows and the two actions on it.
 *
 * @returns the summary and the actions; both actions report their outcome as a message
 */
export function useSkippedEventsActions(): UseSkippedEventsActionsReturn {
  const loading = shallowRef<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });
  const { setMessage } = useMessageStore();
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
    setMessage({
      description,
      success: false,
      title: t('transactions.events.skipped.csv_export_error'),
    });
  }

  async function createCsv(path: string): Promise<void> {
    let message: Message;
    try {
      const success = await exportSkippedEventsCSV(path);
      message = {
        description: success
          ? t('actions.online_events.skipped.csv_export.message.success')
          : t('actions.online_events.skipped.csv_export.message.failure'),
        success,
        title: t('actions.online_events.skipped.csv_export.title'),
      };
    }
    catch (error: unknown) {
      message = {
        description: getErrorMessage(error),
        success: false,
        title: t('actions.online_events.skipped.csv_export.title'),
      };
    }
    setMessage(message);
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
    let message: Message;
    try {
      const { successful, total } = await reProcessSkippedEventsCaller();
      if (successful === 0) {
        message = {
          description: t('transactions.events.skipped.reprocess.failed.no_processed_events'),
          success: false,
          title: t('transactions.events.skipped.reprocess.failed.title'),
        };
      }
      else {
        message = {
          description: successful < total
            ? t('transactions.events.skipped.reprocess.success.some', { successful, total })
            : t('transactions.events.skipped.reprocess.success.all'),
          success: true,
          title: t('transactions.events.skipped.reprocess.success.title'),
        };
      }
    }
    catch (error: unknown) {
      logger.error(error);
      message = {
        description: getErrorMessage(error),
        success: false,
        title: t('transactions.events.skipped.reprocess.failed.title'),
      };
    }
    finally {
      set(loading, false);
    }

    setMessage(message);
    await refreshSkippedEvents();
  }

  return {
    exportCSV,
    loading: readonly(loading),
    locationsData,
    reProcessSkippedEvents,
    skippedEvents,
  };
}
