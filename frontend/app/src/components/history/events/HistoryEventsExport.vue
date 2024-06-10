<script setup lang="ts">
import { TaskType } from '@/types/task-type';
import type { TaskMeta } from '@/types/task';
import type { ActionStatus } from '@/types/action';
import type { HistoryEventRequestPayload } from '@/types/history/events';
import type { Message } from '@rotki/common/lib/messages';

const props = defineProps<{
  filters: HistoryEventRequestPayload;
}>();

const { filters } = toRefs(props);

const { t } = useI18n();

const { appSession, openDirectory } = useInterop();

const { downloadHistoryEventsCSV, exportHistoryEventsCSV }
  = useHistoryEventsApi();

const { setMessage } = useMessageStore();
const { awaitTask } = useTaskStore();
const { notify } = useNotificationsStore();

function showExportCSVError(description: string) {
  setMessage({
    title: t('transactions.events.export.csv_export_error').toString(),
    description,
    success: false,
  });
}

async function createCsv(path: string): Promise<ActionStatus> {
  let message: Message;
  try {
    const taskType = TaskType.EXPORT_HISTORY_EVENTS;
    const { taskId } = await exportHistoryEventsCSV(path, get(filters));
    const { result } = await awaitTask<boolean, TaskMeta>(
      taskId,
      taskType,
      {
        title: t('actions.history_events_export.title').toString(),
      },
    );

    message = {
      title: t('actions.history_events_export.title').toString(),
      description: result
        ? t('actions.history_events_export.message.success').toString()
        : t('actions.history_events_export.message.failure').toString(),
      success: result,
    };
    setMessage(message);
    return {
      success: true,
    };
  }
  catch (error: any) {
    if (!isTaskCancelled(error)) {
      const title = t('actions.history_events_export.title').toString();
      const description = t('actions.history_events_export.message.failure', {
        message: error.message,
      }).toString();

      notify({
        title,
        message: description,
        display: true,
      });
    }
    return {
      success: false,
      message: error.message,
    };
  }
}

async function exportCSV() {
  try {
    if (appSession) {
      const directory = await openDirectory(
        t('common.select_directory').toString(),
      );
      if (!directory)
        return;

      await createCsv(directory);
    }
    else {
      const result = await downloadHistoryEventsCSV(get(filters));
      if (!result.success) {
        showExportCSVError(
          result.message
          ?? t('transactions.events.export.download_failed').toString(),
        );
      }
    }
  }
  catch (error: any) {
    showExportCSVError(error.message);
  }
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
</script>

<template>
  <RuiButton
    color="primary"
    variant="outlined"
    class="!py-2"
    @click="showConfirmation()"
  >
    <template #prepend>
      <RuiIcon name="file-download-line" />
    </template>
    {{ t('common.actions.export_csv') }}
  </RuiButton>
</template>
