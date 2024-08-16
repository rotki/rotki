<script setup lang="ts">
import { type NotificationPayload, type SemiPartial, Severity } from '@rotki/common';
import { TaskType } from '@/types/task-type';
import { jsonTransformer } from '@/services/axios-tranformers';
import type { TaskMeta } from '@/types/task';
import type { HistoryEventRequestPayload } from '@/types/history/events';

const props = defineProps<{
  filters: HistoryEventRequestPayload;
}>();

const { filters } = toRefs(props);

const { t } = useI18n();

const { appSession, openDirectory } = useInterop();

const { exportHistoryEventsCSV } = useHistoryEventsApi();

const { awaitTask, isTaskRunning } = useTaskStore();
const { notify } = useNotificationsStore();

async function createCsv(directoryPath?: string): Promise<{ result: boolean | object; message?: string } | null> {
  try {
    const { taskId } = await exportHistoryEventsCSV(get(filters), directoryPath);
    const { result } = await awaitTask<boolean | object, TaskMeta>(taskId, TaskType.EXPORT_HISTORY_EVENTS, {
      title: t('actions.history_events_export.title'),
      transformer: [jsonTransformer],
    });

    return {
      result,
    };
  }
  catch (error: any) {
    if (isTaskCancelled(error))
      return null;

    return {
      result: false,
      message: error.message,
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

    const { result, message: taskMessage } = response;

    if (appSession || !result) {
      message = {
        title: t('actions.history_events_export.title'),
        message: result
          ? t('actions.history_events_export.message.success')
          : t('actions.history_events_export.message.failure', {
            description: taskMessage,
          }),
        severity: result ? Severity.INFO : Severity.ERROR,
        display: true,
      };
    }
    else {
      downloadFileByTextContent(JSON.stringify(result, null, 2), 'history_events.json', 'application/json');
    }
  }
  catch (error: any) {
    message = {
      title: t('actions.history_events_export.title'),
      message: t('actions.history_events_export.message.failure', {
        description: error.message,
      }),
      severity: Severity.ERROR,
      display: true,
    };
  }

  if (message)
    notify(message);
}

const { show } = useConfirmStore();

function showConfirmation() {
  show(
    {
      title: t('common.actions.export_csv'),
      message: t('transactions.events.export.confirmation_message'),
      type: 'info',
    },
    exportCSV,
  );
}

const taskRunning = isTaskRunning(TaskType.EXPORT_HISTORY_EVENTS);
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
      <RuiIcon name="file-download-line" />
    </template>
    {{ t('common.actions.export_csv') }}
  </RuiButton>
</template>
