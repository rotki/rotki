<script setup lang="ts">
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { type NotificationPayload, type SemiPartial, Severity } from '@rotki/common';
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

const { filters, matchExactEvents } = defineProps<{
  matchExactEvents: boolean;
  filters: HistoryEventRequestPayload;
}>();

const { t } = useI18n({ useScope: 'global' });

const { appSession, openDirectory } = useInterop();

const { downloadHistoryEventsCSV, exportHistoryEventsCSV } = useHistoryEventsApi();

const { submitTask } = useNativeTask();
const { useIsActive } = useTaskCenter();
const { notify } = useNotificationDispatcher();

async function createCsv(directoryPath?: string): Promise<{ result: boolean | { filePath: string }; message?: string } | null> {
  const outcome = await submitTask<boolean | { filePath: string }>({
    id: makeActivityId(ActivityKind.HISTORY_EVENTS, ActivityPart.EXPORT),
    kind: ActivityKind.HISTORY_EVENTS,
    rerunnable: false,
    run: async ({ runTask }): Promise<Result<boolean | { filePath: string }, TaskError>> => mapResult(
      await runTask<boolean | { filePath: string }>(
        () => exportHistoryEventsCSV({
          ...omit(filters, ['limit', 'offset', 'aggregateByGroupIds']),
          matchExactEvents,
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

type ExportMessage = SemiPartial<NotificationPayload, 'title' | 'message'>;

function exportOutcomeMessage(succeeded: boolean, taskMessage?: string): ExportMessage {
  return {
    display: true,
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
async function reportExport(response: Awaited<ReturnType<typeof createCsv>> & object): Promise<ExportMessage | null> {
  const { message: taskMessage, result } = response;

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

    const response = await createCsv(directoryPath);
    if (response === null)
      return;

    message = await reportExport(response);
  }
  catch (error: unknown) {
    message = {
      display: true,
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

const { show } = useConfirmStore();

function showConfirmation() {
  show(
    {
      message: t('transactions.events.export.confirmation_message'),
      title: t('common.actions.export_csv'),
      type: 'info',
    },
    exportCSV,
  );
}

const taskRunning = useIsActive(ActivityKind.HISTORY_EVENTS, ActivityPart.EXPORT);
</script>

<template>
  <RuiTooltip :open-delay="400">
    <template #activator>
      <RuiButton
        color="primary"
        variant="outlined"
        icon
        size="xl"
        class="!rounded"
        :disabled="taskRunning"
        @click="showConfirmation()"
      >
        <RuiIcon name="lu-file-down" />
      </RuiButton>
    </template>
    {{ t('common.actions.export_csv') }}
  </RuiTooltip>
</template>
