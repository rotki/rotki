<script setup lang="ts">
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { HistoryEventsTableEmits } from '../composables/types';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { Collection } from '@/types/collection';
import type {
  HistoryEventEntry,
  HistoryEventRow,
} from '@/types/history/events/schemas';
import DateDisplay from '@/components/display/DateDisplay.vue';
import LazyLoader from '@/components/helper/LazyLoader.vue';
import HistoryEventsAction from '@/components/history/events/HistoryEventsAction.vue';
import HistoryEventsIdentifier from '@/components/history/events/HistoryEventsIdentifier.vue';
import HistoryEventsList from '@/components/history/events/HistoryEventsList.vue';
import IgnoredInAccountingIcon from '@/components/history/IgnoredInAccountingIcon.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useHistoryEventsData } from '../composables/use-history-events-data';
import { useHistoryEventsForms } from '../composables/use-history-events-forms';
import { useHistoryEventsOperations } from '../composables/use-history-events-operations';
import RedecodeConfirmationDialog from './RedecodeConfirmationDialog.vue';

const sort = defineModel<DataTableSortData<HistoryEventEntry>>('sort', { required: true });

const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const props = defineProps<{
  groups: Collection<HistoryEventRow>;
  pageParams: HistoryEventRequestPayload | undefined;
  excludeIgnored: boolean;
  groupLoading: boolean;
  identifiers?: string[];
  highlightedIdentifiers?: string[];
}>();

const emit = defineEmits<HistoryEventsTableEmits>();

defineSlots<{
  'query-status': (props: { colspan: number }) => any;
}>();

const { groupLoading, groups: rawGroups, pageParams } = toRefs(props);

// Event data management
const {
  allEventsMapped,
  displayedEventsMapped,
  entriesFoundTotal,
  events,
  eventsLoading,
  found,
  groups,
  hasIgnoredEvent,
  limit,
  loading,
  sectionLoading,
  showUpgradeRow,
  total,
} = useHistoryEventsData({
  excludeIgnored: toRef(props, 'excludeIgnored'),
  groupLoading,
  groups: rawGroups,
  identifiers: toRef(props, 'identifiers'),
  pageParams,
}, emit);

// Event operations (delete, redecode, etc.)
const {
  confirmDelete,
  confirmRedecode,
  confirmTxAndEventsDelete,
  getItemClass,
  redecode,
  redecodePayload,
  showRedecodeConfirmation,
  suggestNextSequenceId,
  toggle,
} = useHistoryEventsOperations({
  allEventsMapped,
  flattenedEvents: events,
}, emit);

// Form operations
const {
  addEvent,
  addMissingRule,
  editEvent,
} = useHistoryEventsForms(suggestNextSequenceId, emit);

const { t } = useI18n({ useScope: 'global' });

const cols = computed<DataTableColumn<HistoryEventEntry>[]>(() => [{
  cellClass: '!p-0 w-px',
  class: '!p-0 w-px',
  key: 'ignoredInAccounting',
  label: '',
}, {
  cellClass: '!py-2',
  key: 'txHash',
  label: t('transactions.events.headers.event_identifier'),
}, {
  align: 'end',
  cellClass: 'text-no-wrap !py-2 w-[12rem]',
  class: 'w-[12rem]',
  key: 'timestamp',
  label: t('common.datetime'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'w-[1.25rem] !py-2',
  class: 'w-[1.25rem]',
  key: 'action',
  label: '',
}, {
  align: 'end',
  cellClass: '!w-0 !p-0',
  class: '!w-0 !p-0',
  key: 'expand',
  label: '',
}]);

useRememberTableSorting<HistoryEventEntry>(TableId.HISTORY, sort, cols);
</script>

<template>
  <RuiDataTable
    v-model:pagination.external="pagination"
    v-model:sort.external="sort"
    :expanded="groups"
    :cols="cols"
    :rows="groups"
    :loading="loading"
    :item-class="getItemClass"
    :empty="{ label: t('data_table.no_data') }"
    :texts="{
      rowsPerPage: t('data_table.rows_per_page'),
      itemsNumber: t('data_table.items_no'),
      of: t('common.of'),
    }"
    row-attr="identifier"
    outlined
  >
    <template #item.ignoredInAccounting="{ row }">
      <IgnoredInAccountingIcon
        v-if="row.ignoredInAccounting"
        class="ml-4"
      />
      <div
        v-else
        class="min-h-[3.25rem]"
      />
    </template>
    <template #item.txHash="{ row }">
      <LazyLoader class="flex items-center gap-2.5">
        <LocationIcon
          icon
          :item="row.location"
          size="20px"
        />
        <HistoryEventsIdentifier :event="row" />
      </LazyLoader>
    </template>
    <template #item.timestamp="{ row }">
      <LazyLoader>
        <DateDisplay
          :timestamp="row.timestamp"
          milliseconds
        />
      </LazyLoader>
    </template>
    <template #item.action="{ row }">
      <LazyLoader>
        <HistoryEventsAction
          :event="row"
          :loading="eventsLoading"
          @add-event="addEvent($event, row);"
          @toggle-ignore="toggle($event)"
          @redecode="redecode($event, row.eventIdentifier)"
          @delete-tx="confirmTxAndEventsDelete($event)"
        />
      </LazyLoader>
    </template>
    <template #item.expand />
    <template #expanded-item="{ row }">
      <HistoryEventsList
        class="-my-4"
        :class="{ 'opacity-50': row.ignoredInAccounting }"
        :all-events="allEventsMapped[row.eventIdentifier] || []"
        :displayed-events="displayedEventsMapped[row.eventIdentifier] || []"
        :event-group="row"
        :loading="sectionLoading || eventsLoading"
        :has-ignored-event="hasIgnoredEvent"
        :highlighted-identifiers="highlightedIdentifiers"
        @edit-event="editEvent($event, row);"
        @delete-event="confirmDelete($event)"
        @show:missing-rule-action="addMissingRule($event, row);"
        @refresh="emit('refresh')"
      />
    </template>
    <template #body.prepend="{ colspan }">
      <slot
        name="query-status"
        :colspan="colspan"
      />
      <UpgradeRow
        v-if="showUpgradeRow"
        :limit="limit"
        :total="total"
        :found="found"
        :entries-found-total="entriesFoundTotal"
        :colspan="colspan"
        :label="t('common.events')"
      />
    </template>
  </RuiDataTable>
  <RedecodeConfirmationDialog
    v-model:show="showRedecodeConfirmation"
    :payload="redecodePayload"
    @confirm="confirmRedecode($event)"
  />
</template>
