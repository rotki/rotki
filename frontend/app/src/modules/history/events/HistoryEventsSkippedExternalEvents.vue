<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import { type SkippedEventsLocation, useSkippedEventsActions } from '@/modules/history/events/use-skipped-events-actions';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';

const { t } = useI18n({ useScope: 'global' });

const { exportCSV, loading, locationsData, reProcessSkippedEvents, skippedEvents } = useSkippedEventsActions();

const headers: DataTableColumn<SkippedEventsLocation>[] = [
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
</script>

<template>
  <SettingsItem action-key="skippedEvents">
    <template #title>
      {{ t('general_settings.history_event.skipped_events.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.history_event.skipped_events.subtitle') }}
    </template>
    <div class="flex flex-col gap-4">
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
  </SettingsItem>
</template>
