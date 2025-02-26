<script setup lang="ts">
import { logger } from '@/utils/logging';
import { useMessageStore } from '@/store/message';
import { useInterop } from '@/composables/electron-interop';
import { useSkippedHistoryEventsApi } from '@/composables/api/history/events/skipped';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import SettingCategoryHeader from '@/components/settings/SettingCategoryHeader.vue';
import type { DataTableColumn } from '@rotki/ui-library';
import type { Message } from '@rotki/common';
import type { SkippedHistoryEventsSummary } from '@/types/history/events';

interface Location {
  location: string;
  number: number;
}

const { getSkippedEventsSummary } = useSkippedHistoryEventsApi();

const { execute: refreshSkippedEvents, state: skippedEvents } = useAsyncState<SkippedHistoryEventsSummary>(
  getSkippedEventsSummary,
  {
    locations: {},
    total: 0,
  },
  {
    delay: 0,
    immediate: true,
    resetOnExecute: false,
  },
);

const { t } = useI18n();

const headers: DataTableColumn<Location>[] = [
  {
    align: 'center',
    cellClass: 'py-3',
    key: 'location',
    label: t('common.location'),
  },
  {
    align: 'end',
    cellClass: '!pr-12',
    class: '!pr-12',
    key: 'number',
    label: t('transactions.events.skipped.headers.number'),
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
    description,
    success: false,
    title: t('transactions.events.skipped.csv_export_error'),
  });
}

async function createCsv(path: string): Promise<void> {
  let message: Message;
  try {
    const success = await exportSkippedEventsCSV(path);
    message = {
      description: success
        ? t('actions.online_events.skipped.csv_export.message.success')
        : t('actions.online_events.skipped.csv_export.message.failure'),
      success,
      title: t('actions.online_events.skipped.csv_export.title'),
    };
  }
  catch (error: any) {
    message = {
      description: error.message,
      success: false,
      title: t('actions.online_events.skipped.csv_export.title'),
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
    const { successful, total } = await reProcessSkippedEventsCaller();
    if (successful === 0) {
      message = {
        description: t('transactions.events.skipped.reprocess.failed.no_processed_events'),
        success: false,
        title: t('transactions.events.skipped.reprocess.failed.title'),
      };
    }
    else {
      message = {
        description:
          successful < total
            ? t('transactions.events.skipped.reprocess.success.some', {
                successful,
                total,
              })
            : t('transactions.events.skipped.reprocess.success.all'),
        success: true,
        title: t('transactions.events.skipped.reprocess.success.title'),
      };
    }
  }
  catch (error: any) {
    logger.error(error);
    message = {
      description: error.message,
      success: false,
      title: t('transactions.events.skipped.reprocess.failed.title'),
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
    <div class="pb-5 flex flex-wrap gap-4 items-center justify-between">
      <SettingCategoryHeader>
        <template #title>
          {{ t('database_settings.skipped_events.title') }}
        </template>
        <template #subtitle>
          {{ t('database_settings.skipped_events.subtitle') }}
        </template>
      </SettingCategoryHeader>
      <div
        v-if="skippedEvents.total > 0"
        class="flex flex-wrap gap-2"
      >
        <RuiButton
          variant="outlined"
          color="primary"
          @click="exportCSV()"
        >
          <template #prepend>
            <RuiIcon name="lu-file-down" />
          </template>
          {{ t('common.actions.export_csv') }}
        </RuiButton>
        <RuiButton
          color="primary"
          :loading="loading"
          @click="reProcessSkippedEvents()"
        >
          <template #prepend>
            <RuiIcon name="lu-refresh-ccw" />
          </template>
          {{ t('transactions.events.skipped.reprocess.action') }}
        </RuiButton>
      </div>
    </div>
    <RuiDataTable
      :cols="headers"
      :rows="locationsData"
      row-attr="location"
      dense
      striped
      outlined
      class="bg-white dark:bg-transparent"
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
  </div>
</template>
