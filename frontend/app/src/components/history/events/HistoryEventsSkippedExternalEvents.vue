<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { Message } from '@rotki/common';
import type { SkippedHistoryEventsSummary } from '@/types/history/events';

interface Location {
  location: string;
  number: number;
}

const { getSkippedEventsSummary } = useSkippedHistoryEventsApi();

const { state: skippedEvents, execute: refreshSkippedEvents } = useAsyncState<SkippedHistoryEventsSummary>(
  getSkippedEventsSummary,
  {
    locations: {},
    total: 0,
  },
  {
    immediate: true,
    resetOnExecute: false,
    delay: 0,
  },
);

const { t } = useI18n();

const headers: DataTableColumn<Location>[] = [
  {
    label: t('common.location'),
    key: 'location',
    align: 'center',
    cellClass: 'py-3',
  },
  {
    label: t('transactions.events.skipped.headers.number'),
    key: 'number',
    align: 'end',
    cellClass: '!pr-12',
    class: '!pr-12',
  },
];

const locationsData = computed<Location[]>(() =>
  Object.entries(get(skippedEvents).locations).map(([location, number]) => ({
    location,
    number,
  })),
);

const { appSession, openDirectory } = useInterop();

const { downloadSkippedEventsCSV, exportSkippedEventsCSV } = useSkippedHistoryEventsApi();

const { setMessage } = useMessageStore();

function showExportCSVError(description: string) {
  setMessage({
    title: t('transactions.events.skipped.csv_export_error'),
    description,
    success: false,
  });
}

async function createCsv(path: string): Promise<void> {
  let message: Message;
  try {
    const success = await exportSkippedEventsCSV(path);
    message = {
      title: t('actions.online_events.skipped.csv_export.title'),
      description: success
        ? t('actions.online_events.skipped.csv_export.message.success')
        : t('actions.online_events.skipped.csv_export.message.failure'),
      success,
    };
  }
  catch (error: any) {
    message = {
      title: t('actions.online_events.skipped.csv_export.title'),
      description: error.message,
      success: false,
    };
  }
  setMessage(message);
}

async function exportCSV() {
  try {
    if (appSession) {
      const directory = await openDirectory(t('common.select_directory'));
      if (!directory)
        return;

      await createCsv(directory);
    }
    else {
      const result = await downloadSkippedEventsCSV();
      if (!result.success)
        showExportCSVError(result.message ?? t('transactions.events.skipped.download_failed'));
    }
  }
  catch (error: any) {
    showExportCSVError(error.message);
  }
}

const { reProcessSkippedEvents: reProcessSkippedEventsCaller } = useSkippedHistoryEventsApi();

const loading = ref<boolean>(false);

async function reProcessSkippedEvents() {
  set(loading, true);
  let message: Message;
  try {
    const { total, successful } = await reProcessSkippedEventsCaller();
    if (successful === 0) {
      message = {
        title: t('transactions.events.skipped.reprocess.failed.title'),
        description: t('transactions.events.skipped.reprocess.failed.no_processed_events'),
        success: false,
      };
    }
    else {
      message = {
        title: t('transactions.events.skipped.reprocess.success.title'),
        description:
          successful < total
            ? t('transactions.events.skipped.reprocess.success.some', {
              total,
              successful,
            })
            : t('transactions.events.skipped.reprocess.success.all'),
        success: true,
      };
    }
  }
  catch (error: any) {
    logger.error(error);
    message = {
      title: t('transactions.events.skipped.reprocess.failed.title'),
      description: error.message,
      success: false,
    };
  }
  finally {
    set(loading, false);
  }

  setMessage(message);
  await refreshSkippedEvents();
}
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
        row-attr="location"
        dense
        striped
        outlined
        :empty="{
          description: t('transactions.events.skipped.no_skipped_events'),
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
            <td class="text-end pr-12 py-2">
              {{ skippedEvents.total }}
            </td>
          </tr>
        </template>
      </RuiDataTable>

      <div
        v-if="skippedEvents.total > 0"
        class="flex gap-3 mt-6"
      >
        <RuiButton
          variant="outlined"
          color="primary"
          @click="exportCSV()"
        >
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
