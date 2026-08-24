<script setup lang="ts">
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { HistoryEventsTableEmits, HistoryEventsTableHighlight, HistoryEventsTableSource } from '@/modules/history/events/types';
import { provideHistoryEventsRowContext } from '@/modules/history/events/use-history-events-row-context';
import { useHistoryEventsTable } from '@/modules/history/events/use-history-events-table';
import UpgradeRow from '@/modules/history/UpgradeRow.vue';
import HistoryEventsVirtualHeader from './HistoryEventsVirtualHeader.vue';
import HistoryEventsVirtualRow from './HistoryEventsVirtualRow.vue';

const sort = defineModel<DataTableSortData<HistoryEventEntry>>('sort', { required: true });
const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const {
  source,
  highlight,
  hasActiveFilters,
  processing,
  tableHeightOffset,
  hideActions,
  duplicateHandlingStatus,
} = defineProps<{
  /** What to render: the groups plus everything scoping the per-group event fetch. */
  source: HistoryEventsTableSource;
  /** Which rows to call out, and how. */
  highlight?: HistoryEventsTableHighlight;
  hasActiveFilters?: boolean;
  processing?: boolean;
  tableHeightOffset?: number;
  hideActions?: boolean;
  duplicateHandlingStatus?: DuplicateHandlingStatus;
}>();

const emit = defineEmits<HistoryEventsTableEmits>();

defineSlots<{
  'query-status': (props: { colspan: number }) => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const DEFAULT_TABLE_HEIGHT_OFFSET = 390;

const RedecodeConfirmationDialog = defineAsyncComponent(() => import('./RedecodeConfirmationDialog.vue'));

const { redecode, rowContext, shell, virtual } = useHistoryEventsTable({
  duplicateHandlingStatus: () => duplicateHandlingStatus,
  excludeIgnored: () => source.excludeIgnored,
  groupLoading: () => source.groupLoading,
  groups: () => source.groups,
  hideActions: () => hideActions,
  highlightedGroupIdentifier: () => highlight?.groupIdentifier,
  highlightedIdentifiers: () => highlight?.identifiers,
  highlightTypes: () => highlight?.types,
  identifiers: () => source.identifiers,
  pagination,
  requestPayload: () => source.requestPayload,
}, emit);

const { entriesFoundTotal, found, groups, loading, showUpgradeRow, total } = shell;
const { containerProps, list, wrapperProps } = virtual;
const {
  confirm: confirmRedecode,
  hasCustomEvents,
  modelShow: modelShowRedecodeConfirmation,
  payload: redecodePayload,
  showIndexerOptions,
} = redecode;

const tableContainerStyle = computed<{ height: string }>(() => ({
  height: `calc(100vh - ${tableHeightOffset ?? DEFAULT_TABLE_HEIGHT_OFFSET}px)`,
}));

provideHistoryEventsRowContext(rowContext);
</script>

<template>
  <div class="flex flex-col border border-default rounded-lg overflow-hidden bg-slate-50 dark:bg-dark-surface">
    <!-- Sticky Header with Sort + Pagination -->
    <HistoryEventsVirtualHeader
      v-model:sort="sort"
      v-model:pagination="pagination"
      :loading="loading"
      :total="total"
      :found="found"
    />

    <!-- Upgrade Row (premium limit warning) -->
    <UpgradeRow
      v-if="showUpgradeRow"
      :limit="found"
      :total="entriesFoundTotal ?? total"
      class="px-2"
      :colspan="5"
      :label="t('common.events')"
    />

    <!-- Query Status Slot -->
    <slot
      name="query-status"
      :colspan="5"
    />

    <!-- Loading state -->
    <div
      v-if="loading && groups.length === 0"
      :style="tableContainerStyle"
      class="flex items-center justify-center dark:bg-dark-surface"
    >
      <RuiProgress
        circular
        variant="indeterminate"
        color="primary"
        size="32"
      />
    </div>

    <!-- Empty state -->
    <div
      v-else-if="!loading && groups.length === 0"
      :style="tableContainerStyle"
      class="flex flex-col items-center justify-center gap-2 text-rui-text-secondary whitespace-break-spaces text-center"
    >
      <template v-if="hasActiveFilters">
        {{ t('transactions.empty_state.no_data_with_filters') }}
        <RuiButton
          variant="text"
          color="primary"
          class="underline"
          @click="emit('clear-filters')"
        >
          {{ t('transactions.empty_state.clear_filters') }}
        </RuiButton>
      </template>
      <template v-else-if="processing">
        <RuiProgress
          circular
          variant="indeterminate"
          color="primary"
          size="24"
        />
        {{ t('transactions.empty_state.syncing') }}
      </template>
      <template v-else>
        {{ t('transactions.empty_state.no_events') }}
      </template>
    </div>

    <!-- Virtual Scroll Container -->
    <div
      v-else
      v-bind="containerProps"
      :style="tableContainerStyle"
      class="overflow-auto will-change-transform dark:bg-dark-surface"
    >
      <div v-bind="wrapperProps">
        <HistoryEventsVirtualRow
          v-for="{ data: row, index } in list"
          :key="`${row.type}-${row.groupId}-${index}`"
          :row="row"
        />
      </div>
    </div>
  </div>

  <!-- Redecode Confirmation Dialog -->
  <RedecodeConfirmationDialog
    v-model:show="modelShowRedecodeConfirmation"
    :payload="redecodePayload"
    :has-custom-events="hasCustomEvents"
    :show-indexer-options="showIndexerOptions"
    @confirm="confirmRedecode($event)"
  />
</template>
