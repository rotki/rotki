import type { MaybeRefOrGetter, Ref } from 'vue';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { type NotificationPayload, Priority, type SemiPartial, Severity } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

/** What the backend reports: `true` for a file it wrote itself, a path for one to stream back. */
type ExportResult = boolean | { filePath: string };

interface ExportOutcome {
  result: ExportResult;
  message?: string;
}

type ExportMessage = SemiPartial<NotificationPayload, 'title' | 'message'>;

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
   * @returns the outcome, or `null` when the failure was already reported by the task centre
   */
  async function createCsv(directoryPath?: string): Promise<ExportOutcome | null> {
    const outcome = await submitTask<ExportResult>({
      id: makeActivityId(ActivityKind.HISTORY_EVENTS, ActivityPart.EXPORT),
      kind: ActivityKind.HISTORY_EVENTS,
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
      subtitle: activityLabel(ActivityKind.HISTORY_EVENTS, ActivityPart.EXPORT),
      title: t('task_center.group.history_events'),
    });

    if (!isErr(outcome))
      return { result: outcome.value };

    if (!isActionable(outcome.error))
      return null;

    return {
      message: outcome.error.message,
      result: false,
    };
  }

  function exportOutcomeMessage(succeeded: boolean, taskMessage?: string): ExportMessage {
    return {
      message: succeeded
        ? t('actions.history_events_export.message.success')
        : t('actions.history_events_export.message.failure', { description: taskMessage }),
      severity: succeeded ? Severity.INFO : Severity.ERROR,
      title: t('actions.history_events_export.title'),
    };
  }

  /**
   * In an app session the file was written where the user chose, so the outcome is only reported. A
   * browser session instead gets the generated file streamed back, and only a failure is reported.
   */
  async function reportExport(outcome: ExportOutcome): Promise<ExportMessage | null> {
    const { message: taskMessage, result } = outcome;

    if (appSession || !result)
      return exportOutcomeMessage(!!result, taskMessage);

    if (result !== true && 'filePath' in result)
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
        message: t('actions.history_events_export.message.failure', {
          description: getErrorMessage(error),
        }),
        severity: Severity.ERROR,
        title: t('actions.history_events_export.title'),
      };
    }

    if (message)
      notify({ ...message, priority: Priority.HIGH });
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
    taskRunning: useIsActive(ActivityKind.HISTORY_EVENTS, ActivityPart.EXPORT),
  };
}
