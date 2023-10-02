<script setup lang="ts">
import { type DataTableColumn } from '@rotki/ui-library-compat';
import { type Message } from '@rotki/common/lib/messages';
import { type SkippedHistoryEventsSummary } from '@/types/history/events';

const props = defineProps<{
  skippedEvents: SkippedHistoryEventsSummary;
}>();

const emit = defineEmits<{
  (e: 'reprocessed'): void;
}>();

const { skippedEvents } = toRefs(props);

const dialogOpen: Ref<boolean> = ref(false);

const { t } = useI18n();

const headers: DataTableColumn[] = [
  {
    label: t('common.location'),
    key: 'location',
    align: 'center',
    cellClass: 'py-0'
  },
  {
    label: t('transactions.events.skipped.headers.number'),
    key: 'number',
    align: 'end',
    cellClass: '!pr-12',
    class: '!pr-12'
  }
];

const locationsData = computed(() =>
  Object.entries(get(skippedEvents).locations).map(([location, number]) => ({
    location,
    number
  }))
);

const { appSession, openDirectory } = useInterop();

const { downloadSkippedEventsCSV, exportSkippedEventsCSV } =
  useSkippedHistoryEventsApi();

const { setMessage } = useMessageStore();

const showExportCSVError = (description: string) => {
  setMessage({
    title: t('transactions.events.skipped.csv_export_error').toString(),
    description,
    success: false
  });
};

const createCsv = async (path: string): Promise<void> => {
  let message: Message;
  try {
    const success = await exportSkippedEventsCSV(path);
    message = {
      title: t('actions.online_events.skipped.csv_export.title').toString(),
      description: success
        ? t(
            'actions.online_events.skipped.csv_export.message.success'
          ).toString()
        : t(
            'actions.online_events.skipped.csv_export.message.failure'
          ).toString(),
      success
    };
  } catch (e: any) {
    message = {
      title: t('actions.online_events.skipped.csv_export.title').toString(),
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
      const result = await downloadSkippedEventsCSV();
      if (!result.success) {
        showExportCSVError(
          result.message ??
            t('transactions.events.skipped.download_failed').toString()
        );
      }
    }
  } catch (e: any) {
    showExportCSVError(e.message);
  }
};

const { reProcessSkippedEvents: reProcessSkippedEventsCaller } =
  useSkippedHistoryEventsApi();

const loading: Ref<boolean> = ref(false);
const reProcessSkippedEvents = async () => {
  set(loading, true);
  let message: Message;
  try {
    const { total, successfull } = await reProcessSkippedEventsCaller();
    if (successfull === 0) {
      message = {
        title: t('transactions.events.skipped.reprocess.failed.title'),
        description: t(
          'transactions.events.skipped.reprocess.failed.no_processed_events'
        ),
        success: false
      };
    } else {
      message = {
        title: t('transactions.events.skipped.reprocess.success.title'),
        description:
          successfull < total
            ? t('transactions.events.skipped.reprocess.success.some', {
                total,
                successfull
              })
            : t('transactions.events.skipped.reprocess.success.all'),
        success: true
      };
      emit('reprocessed');
    }
  } catch (e: any) {
    logger.error(e);
    message = {
      title: t('transactions.events.skipped.reprocess.failed.title').toString(),
      description: e.message,
      success: false
    };
  } finally {
    set(loading, false);
  }

  setMessage(message);
};
</script>

<template>
  <VBottomSheet v-model="dialogOpen" max-width="500">
    <template #activator="{ on }">
      <RuiButton
        color="secondary"
        variant="outlined"
        :disabled="!skippedEvents.total"
        v-on="on"
      >
        <template #prepend>
          <RuiIcon name="skip-right-line" />
        </template>
        {{ t('transactions.events.skipped.title') }}
        <template #append>
          <RuiChip
            size="sm"
            color="secondary"
            :label="skippedEvents.total"
            class="py-0 px-0"
            :disabled="!skippedEvents.total"
          />
        </template>
      </RuiButton>
    </template>

    <Card contained>
      <template #title>
        {{ t('transactions.events.skipped.title') }}
      </template>

      <template #details>
        <RuiButton icon variant="text" size="sm" @click="dialogOpen = false">
          <RuiIcon name="close-line" />
        </RuiButton>
      </template>

      <div class="pt-2">
        <RuiDataTable :cols="headers" :rows="locationsData" dense outlined>
          <template #item.location="{ row }">
            <LocationDisplay :identifier="row.location" />
          </template>
          <template #item.number="{ row }">
            {{ row.number }}
          </template>
          <template #tfoot>
            <tr>
              <th>{{ t('common.total') }}</th>
              <td class="text-end pr-12 py-2">{{ skippedEvents.total }}</td>
            </tr>
          </template>
        </RuiDataTable>
      </div>

      <template #buttons>
        <div class="w-full flex justify-end gap-2">
          <RuiButton variant="outlined" color="primary" @click="exportCSV()">
            <template #prepend>
              <RuiIcon name="file-download-line" />
            </template>
            {{ t('common.actions.export_csv') }}
          </RuiButton>
          <RuiButton
            color="primary"
            :loading="loading"
            @click="reProcessSkippedEvents()"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('transactions.events.skipped.reprocess.action') }}
          </RuiButton>
        </div>
      </template>
    </Card>
  </VBottomSheet>
</template>
