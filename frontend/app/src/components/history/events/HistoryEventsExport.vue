<script setup lang="ts">
import type { HistoryEventRequestPayload } from '@/types/history/events';
import type { TaskMeta } from '@/types/task';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useInterop } from '@/composables/electron-interop';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { type NotificationPayload, type SemiPartial, Severity } from '@rotki/common';

const props = defineProps<{
  filters: HistoryEventRequestPayload;
}>();

const { filters } = toRefs(props);

const { t } = useI18n();

const { appSession, openDirectory } = useInterop();

const { downloadHistoryEventsCSV, exportHistoryEventsCSV } = useHistoryEventsApi();

const { awaitTask, useIsTaskRunning } = useTaskStore();
const { notify } = useNotificationsStore();

async function createCsv(directoryPath?: string): Promise<{ result: boolean | { filePath: string }; message?: string } | null> {
  try {
    const { taskId } = await exportHistoryEventsCSV(get(filters), directoryPath);
    const { result } = await awaitTask<boolean | { filePath: string }, TaskMeta>(taskId, TaskType.EXPORT_HISTORY_EVENTS, {
      title: t('actions.history_events_export.title'),
    });

    return {
      result,
    };
  }
  catch (error: any) {
    if (isTaskCancelled(error))
      return null;

    return {
      message: error.message,
      result: false,
    };
  }
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
  catch (error: any) {
    message = {
      display: true,
      message: t('actions.history_events_export.message.failure', {
        description: error.message,
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
  <RuiButton
    color="primary"
    variant="outlined"
    class="!py-2"
    :disabled="taskRunning"
    @click="showConfirmation()"
  >
    <template #prepend>
      <RuiIcon name="lu-file-down" />
    </template>
    {{ t('common.actions.export_csv') }}
  </RuiButton>
</template>
