<script setup lang="ts">
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import type { HistoryEventsTableEmits, HistoryEventsTableHighlight, HistoryEventsTableSource } from '@/modules/history/events/types';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import TableFailureDescription from '@/modules/core/table/TableFailureDescription.vue';
import { useTableEmptyState, useTableFetchError } from '@/modules/core/table/use-table-empty-state';
import { provideHistoryEventsRowContext } from '@/modules/history/events/use-history-events-row-context';
import { useHistoryEventsTable } from '@/modules/history/events/use-history-events-table';
import UpgradeRow from '@/modules/history/UpgradeRow.vue';
import FailureStrip from '@/modules/shell/components/FailureStrip.vue';
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
const failureMessage = useFailureMessage();

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

const { entriesFoundTotal, eventsError, found, groups, loading, retryEvents, showUpgradeRow, total } = shell;
const { containerProps, list, wrapperProps } = virtual;
const {
  confirm: confirmRedecode,
  hasCustomEvents,
  modelShow: modelShowRedecodeConfirmation,
  payload: redecodePayload,
  showIndexerOptions,
} = redecode;

const fetchError = useTableFetchError();
const emptyState = useTableEmptyState();
const fetchFailed = computed<boolean>(() => !!(fetchError && get(fetchError)));

const tableHeight = computed<string>(() => `calc(100vh - ${tableHeightOffset ?? DEFAULT_TABLE_HEIGHT_OFFSET}px)`);

const tableContainerStyle = computed<{ height: string }>(() => ({
  height: get(tableHeight),
}));

/**
 * A message or spinner has nothing to scroll, so on a tall window it would float in the middle of
 * an empty viewport-high box, far below the table header. It gets the table's height up to a cap.
 */
const placeholderStyle = computed<{ height: string }>(() => ({
  height: `min(${get(tableHeight)}, 24rem)`,
}));

provideHistoryEventsRowContext(rowContext);
</script>

<template>
  <div class="flex flex-col overflow-hidden bg-slate-50 dark:bg-rui-background">
    <HistoryEventsVirtualHeader
      v-model:sort="sort"
      v-model:pagination="pagination"
      :loading="loading"
      :found="found"
    />

    <UpgradeRow
      v-if="showUpgradeRow"
      :limit="found"
      :total="entriesFoundTotal ?? total"
      class="px-2"
      :colspan="5"
      :label="t('plan_limit.labels.events')"
    />

    <slot
      name="query-status"
      :colspan="5"
    />

    <FailureStrip
      v-if="eventsError && groups.length > 0"
      class="m-2"
      :title="t('data_table.fetch_failed')"
      :message="failureMessage(eventsError)"
      data-testid="history-events-events-error"
      @retry="retryEvents()"
    />

    <div
      v-if="loading && groups.length === 0"
      :style="placeholderStyle"
      class="flex items-center justify-center dark:bg-rui-background"
    >
      <RuiProgress
        circular
        variant="indeterminate"
        color="primary"
        size="32"
      />
    </div>

    <div
      v-else-if="!loading && groups.length === 0"
      :style="placeholderStyle"
      class="flex flex-col items-center justify-center px-4"
    >
      <RuiTableEmptyState
        v-if="fetchFailed"
        class="max-w-md"
        :label="emptyState.label"
        data-testid="history-events-fetch-error"
      >
        <template #description>
          <TableFailureDescription
            :message="emptyState.description ?? ''"
            @retry="emit('refetch')"
          />
        </template>
      </RuiTableEmptyState>
      <RuiTableEmptyState
        v-else-if="hasActiveFilters"
        :label="t('transactions.empty_state.no_data_with_filters')"
      >
        <template #description>
          <RuiButton
            variant="outlined"
            color="primary"
            size="sm"
            data-testid="history-events-clear-filters"
            @click="emit('clear-filters')"
          >
            <template #prepend>
              <RuiIcon
                name="lu-filter-x"
                size="14"
              />
            </template>
            {{ t('transactions.empty_state.clear_filters') }}
          </RuiButton>
        </template>
      </RuiTableEmptyState>
      <div
        v-else-if="processing"
        class="flex flex-col items-center gap-3 max-w-md text-center"
      >
        <RuiProgress
          circular
          variant="indeterminate"
          color="primary"
          size="32"
        />
        <div class="font-medium text-rui-text">
          {{ t('transactions.empty_state.syncing') }}
        </div>
        <div class="text-sm text-rui-text-secondary">
          {{ t('transactions.empty_state.syncing_hint') }}
        </div>
      </div>
      <RuiTableEmptyState
        v-else
        class="max-w-md"
        :label="t('transactions.empty_state.no_events')"
        :description="t('transactions.empty_state.no_events_hint')"
      />
    </div>

    <div
      v-else
      v-bind="containerProps"
      :style="tableContainerStyle"
      class="overflow-auto will-change-transform dark:bg-rui-background"
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

  <RedecodeConfirmationDialog
    v-model:show="modelShowRedecodeConfirmation"
    :payload="redecodePayload"
    :has-custom-events="hasCustomEvents"
    :show-indexer-options="showIndexerOptions"
    @confirm="confirmRedecode($event)"
  />
</template>
