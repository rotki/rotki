import type { MaybeRefOrGetter, Ref } from 'vue';
import type { TaskError } from '@/modules/core/tasks/task-result';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { type Notification, NotificationKind, Severity } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { activityLabelOf } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';
import { historyEventsExportActivity } from './history-events.activity';

/** What the backend reports: `true` for a file it wrote itself, a path for one to stream back. */
type ExportResult = boolean | { filePath: string };

interface ExportOutcome {
  result: ExportResult;
}

type ExportMessage = Notification;

interface UseHistoryEventsExportReturn {
  /** Whether an export is already running, so the caller can disable its control. */
  taskRunning: Ref<boolean>;
  /** Asks the user to confirm, then exports. */
  showConfirmation: () => void;
}

/**
 * Exports the events matching the current filters to CSV.
 *
 * @param filters - the table's filters; paging and grouping are dropped, since the export is whole
 * @param matchExactEvents - whether to export the matched events rather than their groups
 * @returns the running flag and the confirm-then-export entry point
 */
export function useHistoryEventsExport(
  filters: MaybeRefOrGetter<HistoryEventRequestPayload>,
  matchExactEvents: MaybeRefOrGetter<boolean>,
): UseHistoryEventsExportReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { appSession, openDirectory } = useInterop();
  const { downloadHistoryEventsCSV, exportHistoryEventsCSV } = useHistoryEventsApi();
  const { submitTask } = useNativeTask();
  const { useIsActive } = useTaskCenter();
  const { notify } = useNotificationDispatcher();
  const { show } = useConfirmStore();

  /**
   * @returns the outcome, or `null` when the task failed or was cancelled, which its dock row reports
   */
  async function createCsv(directoryPath?: string): Promise<ExportOutcome | null> {
    const outcome = await submitTask<ExportResult>({
      id: historyEventsExportActivity.id(),
      kind: historyEventsExportActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<ExportResult, TaskError>> => mapResult(
        await runTask<ExportResult>(
          async () => exportHistoryEventsCSV({
            ...omit(toValue(filters), ['limit', 'offset', 'aggregateByGroupIds']),
            matchExactEvents: toValue(matchExactEvents),
          }, directoryPath),
        ),
        value => value,
      ),
      subtitle: activityLabelOf(historyEventsExportActivity),
      title: t('task_center.group.history_events'),
    });

    return isErr(outcome) ? null : { result: outcome.value };
  }

  /**
   * In an app session the file was written where the user chose, so the success is only reported. A
   * browser session instead gets the generated file streamed back. A failure is the task's to report.
   */
  async function reportExport({ result }: ExportOutcome): Promise<ExportMessage | null> {
    if (appSession) {
      return {
        kind: NotificationKind.RESULT,
        message: t('actions.history_events_export.message.success'),
        severity: Severity.INFO,
        title: t('actions.history_events_export.title'),
      };
    }

    if (typeof result === 'object')
      await downloadHistoryEventsCSV(result.filePath);

    return null;
  }

  async function exportCSV(): Promise<void> {
    let message: ExportMessage | null = null;

    try {
      let directoryPath;
      if (appSession) {
        directoryPath = await openDirectory(t('common.select_directory'));
        if (!directoryPath)
          return;
      }

      const outcome = await createCsv(directoryPath);
      if (outcome === null)
        return;

      message = await reportExport(outcome);
    }
    catch (error: unknown) {
      message = {
        kind: NotificationKind.RESULT,
        message: t('actions.history_events_export.message.failure', {
          description: getErrorMessage(error),
        }),
        severity: Severity.ERROR,
        title: t('actions.history_events_export.title'),
      };
    }

    if (message)
      notify(message);
  }

  function showConfirmation(): void {
    show(
      {
        message: t('transactions.events.export.confirmation_message'),
        title: t('common.actions.export_csv'),
        type: 'info',
      },
      exportCSV,
    );
  }

  return {
    showConfirmation,
    taskRunning: useIsActive(historyEventsExportActivity.kind, ...historyEventsExportActivity.partsOf()),
  };
}
