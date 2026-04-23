<script setup lang="ts">
import type { TaskMeta } from '@/modules/core/tasks/types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import { type NotificationPayload, type SemiPartial, Severity } from '@rotki/common';
import { omit } from 'es-toolkit';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const { filters, matchExactEvents } = defineProps<{
  matchExactEvents: boolean;
  filters: HistoryEventRequestPayload;
}>();

const { t } = useI18n({ useScope: 'global' });

const { appSession, openDirectory } = useInterop();

const { downloadHistoryEventsCSV, exportHistoryEventsCSV } = useHistoryEventsApi();

const { runTask } = useTaskHandler();
const { useIsTaskRunning } = useTaskStore();
const { notify } = useNotificationDispatcher();

async function createCsv(directoryPath?: string): Promise<{ result: boolean | { filePath: string }; message?: string } | null> {
  const outcome = await runTask<boolean | { filePath: string }, TaskMeta>(
    () => exportHistoryEventsCSV({
      ...omit(filters, ['limit', 'offset', 'aggregateByGroupIds']),
      matchExactEvents,
    }, directoryPath),
    { type: TaskType.EXPORT_HISTORY_EVENTS, meta: { title: t('actions.history_events_export.title') } },
  );

  if (outcome.success)
    return { result: outcome.result };

  if (!isActionableFailure(outcome))
    return null;

  return {
    message: outcome.message,
    result: false,
  };
}

async function exportCSV(): Promise<void> {
  let message: SemiPartial<NotificationPayload, 'title' | 'message'> | null = null;

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

    const { message: taskMessage, result } = response;

    if (appSession || !result) {
      message = {
        display: true,
        message: result
          ? t('actions.history_events_export.message.success')
          : t('actions.history_events_export.message.failure', {
              description: taskMessage,
            }),
        severity: result ? Severity.INFO : Severity.ERROR,
        title: t('actions.history_events_export.title'),
      };
    }
    else if (result !== true && 'filePath' in result) {
      await downloadHistoryEventsCSV(result.filePath);
    }
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

const taskRunning = useIsTaskRunning(TaskType.EXPORT_HISTORY_EVENTS);
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
