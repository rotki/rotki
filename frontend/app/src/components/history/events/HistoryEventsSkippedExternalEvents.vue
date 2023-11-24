<script setup lang="ts">
import { type DataTableColumn } from '@rotki/ui-library-compat';
import { type Message } from '@rotki/common/lib/messages';
import { type SkippedHistoryEventsSummary } from '@/types/history/events';

const { getSkippedEventsSummary } = useSkippedHistoryEventsApi();

const { state: skippedEvents, execute } =
  useAsyncState<SkippedHistoryEventsSummary>(
    getSkippedEventsSummary,
    {
      locations: {},
      total: 0
    },
    {
      immediate: true,
      resetOnExecute: false,
      delay: 0
    }
  );

onMounted(() => {
  execute();
});

const { t } = useI18n();

const headers: DataTableColumn[] = [
  {
    label: t('common.location'),
    key: 'location',
    align: 'center',
    cellClass: 'py-3'
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
    const { total, successful } = await reProcessSkippedEventsCaller();
    if (successful === 0) {
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
          successful < total
            ? t('transactions.events.skipped.reprocess.success.some', {
                total,
                successful
              })
            : t('transactions.events.skipped.reprocess.success.all'),
        success: true
      };
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
  <div>
    <div class="mb-6 gap-4">
      <div class="text-h6">
        {{ t('transactions.events.skipped.title') }}
      </div>
    </div>

    <div class="max-w-[40rem]">
      <RuiDataTable
        :cols="headers"
        :rows="locationsData"
        dense
        striped
        outlined
        :empty="{
          description: t('transactions.events.skipped.no_skipped_events')
        }"
      >
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

      <div v-if="skippedEvents.total > 0" class="flex gap-3 mt-6">
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
    </div>
  </div>
</template>
