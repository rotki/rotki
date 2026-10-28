<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { DuplicateRow } from '@/modules/history/events/use-customized-event-duplicates';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import { HISTORY_DIALOG_MAX_HEIGHT } from '@/modules/history/events/dialog-layout';
import HistoryEventAccount from '@/modules/history/events/HistoryEventAccount.vue';
import HistoryEventsIdentifier from '@/modules/history/events/HistoryEventsIdentifier.vue';
import LocationDisplay from '@/modules/history/LocationDisplay.vue';
import DateDisplay from '@/modules/shell/components/display/DateDisplay.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';

const selected = defineModel<string[]>('selected', { default: () => [] });

const {
  description,
  error,
  rows,
  loading = false,
} = defineProps<{
  description: string;
  loading?: boolean;
  rows: DuplicateRow[];
  /** why the tab could not be read, shown in place of the rows or above the rows an earlier read left */
  error?: unknown;
}>();

const emit = defineEmits<{
  'retry': [];
  'show-in-history': [];
}>();

defineSlots<{
  actions: (props: { row: DuplicateRow }) => any;
}>();

const { t } = useI18n({ useScope: 'global' });
const failureMessage = useFailureMessage();

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
    <ScrollableDialogContent :max-height="HISTORY_DIALOG_MAX_HEIGHT">
      <RuiDataTable
        v-model="selected"
        :cols="columns"
        :rows="rows"
        row-attr="groupIdentifier"
        outlined
        dense
        multi-page-select
        :loading="loading"
        :empty="error ? { label: t('customized_event_duplicates.load_failed') } : { description: t('customized_event_duplicates.no_items') }"
      >
        <template
          v-if="error"
          #empty-description
        >
          <TableFailureDescription
            :message="failureMessage(error)"
            @retry="emit('retry')"
          />
        </template>
        <template
          v-if="error && rows.length > 0"
          #body.prepend
        >
          <tr>
            <td :colspan="columns.length + 1">
              <FailureStrip
                in-table
                :title="t('customized_event_duplicates.load_failed')"
                :failure="error"
                data-testid="duplicates-load-error"
                @retry="emit('retry')"
              />
            </td>
          </tr>
        </template>
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
    </ScrollableDialogContent>
  </div>
</template>
