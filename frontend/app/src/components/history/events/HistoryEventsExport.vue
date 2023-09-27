<script setup lang="ts">
import { type Message } from '@rotki/common/lib/messages';
import { type HistoryEventRequestPayload } from '@/types/history/events';

const props = defineProps<{
  filters: HistoryEventRequestPayload;
}>();

const { filters } = toRefs(props);

const { t } = useI18n();

const { appSession, openDirectory } = useInterop();

const { downloadHistoryEventsCSV, exportHistoryEventsCSV } =
  useHistoryEventsApi();

const { setMessage } = useMessageStore();

const showExportCSVError = (description: string) => {
  setMessage({
    title: t('transactions.events.export.csv_export_error').toString(),
    description,
    success: false
  });
};

const createCsv = async (path: string): Promise<void> => {
  let message: Message;
  try {
    const success = await exportHistoryEventsCSV(path, get(filters));
    message = {
      title: t('actions.history_events_export.title').toString(),
      description: success
        ? t('actions.history_events_export.message.success').toString()
        : t('actions.history_events_export.message.failure').toString(),
      success
    };
  } catch (e: any) {
    message = {
      title: t('actions.history_events_export.title').toString(),
      description: e.message,
      success: false
    };
  }
  setMessage(message);
};

const exportCSV = async () => {
  try {
    if (appSession) {
      const directory = await openDirectory(
        t('common.select_directory').toString()
      );
      if (!directory) {
        return;
      }
      await createCsv(directory);
    } else {
      const result = await downloadHistoryEventsCSV(get(filters));
      if (!result.success) {
        showExportCSVError(
          result.message ??
            t('transactions.events.export.download_failed').toString()
        );
      }
    }
  } catch (e: any) {
    showExportCSVError(e.message);
  }
};

const { show } = useConfirmStore();

const showConfirmation = () => {
  show(
    {
      title: t('common.actions.export_csv'),
      message: t('transactions.events.export.confirmation_message'),
      type: 'info'
    },
    exportCSV
  );
};
</script>

<template>
  <RuiButton color="primary" variant="outlined" @click="showConfirmation()">
    <template #prepend>
      <RuiIcon name="file-download-line" />
    </template>
    {{ t('common.actions.export_csv') }}
  </RuiButton>
</template>
