<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { DuplicateRow } from '@/composables/history/events/use-customized-event-duplicates';
import DateDisplay from '@/components/display/DateDisplay.vue';
import HistoryEventAccount from '@/components/history/events/HistoryEventAccount.vue';
import HistoryEventsIdentifier from '@/components/history/events/HistoryEventsIdentifier.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';

const selected = defineModel<string[]>('selected', { default: () => [] });

const {
  description,
  rows,
  loading = false,
} = defineProps<{
  description: string;
  loading?: boolean;
  rows: DuplicateRow[];
}>();

const emit = defineEmits<{
  'show-in-history': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const columns = computed<DataTableColumn<DuplicateRow>[]>(() => [
  {
    key: 'timestamp',
    label: t('common.datetime'),
  },
  {
    key: 'txHash',
    label: t('customized_event_duplicates.columns.tx_hash'),
  },
  {
    align: 'center',
    key: 'location',
    label: t('common.location'),
  },
  {
    key: 'actions',
    label: '',
  },
]);
</script>

<template>
  <div>
    <div class="flex items-center justify-between gap-2 mb-4">
      <p class="text-body-2 text-rui-text-secondary">
        {{ description }}
      </p>
      <RuiButton
        size="sm"
        color="primary"
        variant="outlined"
        :disabled="rows.length === 0"
        @click="emit('show-in-history')"
      >
        <template #prepend>
          <RuiIcon
            size="18"
            name="lu-external-link"
          />
        </template>
        {{ t('customized_event_duplicates.actions.show_in_history') }}
      </RuiButton>
    </div>
    <RuiDataTable
      v-model="selected"
      :cols="columns"
      :rows="rows"
      row-attr="groupIdentifier"
      outlined
      dense
      multi-page-select
      :loading="loading"
      class="max-h-[calc(100vh-23rem)] table-inside-dialog"
      :empty="{ description: t('customized_event_duplicates.no_items') }"
    >
      <template #item.timestamp="{ row }">
        <DateDisplay
          :timestamp="row.timestamp"
          milliseconds
        />
      </template>
      <template #item.txHash="{ row }">
        <div class="flex flex-col gap-1">
          <HistoryEventsIdentifier :event="row.entry" />
          <HistoryEventAccount
            v-if="row.locationLabel"
            :location="row.location"
            :location-label="row.locationLabel"
            class="text-sm min-w-0"
          />
        </div>
      </template>
      <template #item.location="{ row }">
        <LocationDisplay
          size="24px"
          horizontal
          :identifier="row.location"
        />
      </template>
      <template #item.actions="{ row }">
        <slot
          name="actions"
          :row="row"
        />
      </template>
    </RuiDataTable>
  </div>
</template>
