<script setup lang="ts">
import type { DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { DuplicateHandlingStatus, HighlightType } from '@/composables/history/events/types';
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { HistoryEventsTableEmits } from '@/modules/history/events/types';
import type { Collection } from '@/types/collection';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { useHistoryEventsData } from '../composables/use-history-events-data';
import { useHistoryEventsForms } from '../composables/use-history-events-forms';
import { useHistoryEventsOperations } from '../composables/use-history-events-operations';
import { useVirtualRows } from '../composables/use-virtual-rows';
import { useVirtualScrollHighlight } from '../composables/use-virtual-scroll-highlight';
import HistoryEventsDetailItem from './HistoryEventsDetailItem.vue';
import HistoryEventsGroupItem from './HistoryEventsGroupItem.vue';
import HistoryEventsLoadMoreRow from './HistoryEventsLoadMoreRow.vue';
import HistoryEventsMatchedMovementItem from './HistoryEventsMatchedMovementItem.vue';
import HistoryEventsSwapCollapseRow from './HistoryEventsSwapCollapseRow.vue';
import HistoryEventsSwapItem from './HistoryEventsSwapItem.vue';
import HistoryEventsVirtualHeader from './HistoryEventsVirtualHeader.vue';

const sort = defineModel<DataTableSortData<HistoryEventEntry>>('sort', { required: true });
const pagination = defineModel<TablePaginationData>('pagination', { required: true });

const props = defineProps<{
  groups: Collection<HistoryEventRow>;
  pageParams: HistoryEventRequestPayload | undefined;
  excludeIgnored: boolean;
  groupLoading: boolean;
  hasActiveFilters?: boolean;
  tableHeightOffset?: number;
  identifiers?: string[];
  highlightedIdentifiers?: string[];
  highlightTypes?: Record<string, HighlightType>;
  hideActions?: boolean;
  selection?: UseHistoryEventsSelectionModeReturn;
  matchExactEvents?: boolean;
  duplicateHandlingStatus?: DuplicateHandlingStatus;
}>();

const emit = defineEmits<HistoryEventsTableEmits>();

defineSlots<{
  'query-status': (props: { colspan: number }) => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const DEFAULT_TABLE_HEIGHT_OFFSET = 390;

const tableContainerStyle = computed<{ height: string }>(() => ({
  height: `calc(100vh - ${props.tableHeightOffset ?? DEFAULT_TABLE_HEIGHT_OFFSET}px)`,
}));

const RedecodeConfirmationDialog = defineAsyncComponent(() => import('./RedecodeConfirmationDialog.vue'));
const { groupLoading, groups: rawGroups, pageParams } = toRefs(props);

// Event data management
const {
  completeEventsMapped,
  displayedEventsMapped,
  entriesFoundTotal,
  events,
  eventsLoading,
  found,
  getCompleteEventsForItem,
  getCompleteSubgroupEvents,
  getGroupEvents,
  groups,
  groupsShowingIgnoredAssets,
  groupsWithHiddenIgnoredAssets,
  isSubgroupIncomplete,
  limit,
  loading,
  rawEvents,
  showUpgradeRow,
  toggleShowIgnoredAssets,
  total,
} = useHistoryEventsData({
  excludeIgnored: toRef(props, 'excludeIgnored'),
  groupLoading,
  groups: rawGroups,
  identifiers: toRef(props, 'identifiers'),
  pageParams,
}, emit);

// Virtual rows - flatten groups into virtual row list
// Use displayedEventsMapped for display (respects excludeIgnored filter)
const { flattenedRows, getCardHeight, getRowHeight, loadMoreEvents, toggleMovementExpanded, toggleSwapExpanded } = useVirtualRows(
  groups,
  displayedEventsMapped,
  isSubgroupIncomplete,
);

// Virtual list with scroll and highlight management
const {
  containerProps,
  getHighlightType,
  getSwapHighlightType,
  isCardLayout,
  isHighlighted,
  isSwapHighlighted,
  virtualList,
  wrapperProps,
} = useVirtualScrollHighlight({
  flattenedRows,
  getRowHeight,
  getCardHeight,
  highlightedIdentifiers: computed(() => props.highlightedIdentifiers),
  highlightTypes: computed(() => props.highlightTypes),
  loading,
  pagination,
});

// Variant based on breakpoint
const itemVariant = computed<'row' | 'card'>(() => get(isCardLayout) ? 'card' : 'row');

// Event operations (delete, redecode, etc.)
const {
  confirmDelete,
  confirmRedecode,
  confirmTxAndEventsDelete,
  confirmUnlink,
  unlinkGroup,
  hasCustomEvents,
  redecode,
  redecodePayload,
  redecodeWithOptions,
  showIndexerOptions,
  showRedecodeConfirmation,
  suggestNextSequenceId,
  toggle,
} = useHistoryEventsOperations({
  completeEventsMapped,
  flattenedEvents: events,
}, emit);

// Form operations
const {
  addEvent,
  addMissingRule,
  editEvent,
} = useHistoryEventsForms(suggestNextSequenceId, emit);

// Emit event IDs when events change
watch([events, completeEventsMapped, rawEvents], ([newEvents, groupedEvents, rawEventsData]) => {
  const eventIds = newEvents.map(event => event.identifier);
  emit('update-event-ids', { eventIds, groupedEvents, rawEvents: rawEventsData });
}, { immediate: true });

// Create a lookup map for O(1) group access
const groupsMap = computed<Map<string, HistoryEventEntry>>(() => {
  const map = new Map<string, HistoryEventEntry>();
  for (const group of get(groups)) {
    map.set(group.groupIdentifier, group);
  }
  return map;
});

// Helper to find group by ID (O(1) lookup)
function findGroup(groupId: string): HistoryEventEntry | undefined {
  return get(groupsMap).get(groupId);
}

// Handler for edit event with group lookup
function handleEditEvent(data: Parameters<typeof editEvent>[0], groupId: string): void {
  const group = findGroup(groupId);
  if (group)
    editEvent(data, group);
}

// Handler for missing rule action with group lookup
function handleMissingRuleAction(data: Parameters<typeof addMissingRule>[0], groupId: string): void {
  const group = findGroup(groupId);
  if (group)
    addMissingRule(data, group);
}

// Helper to check if a group has hidden events due to ignored assets
function hasHiddenIgnoredAssets(groupId: string): boolean {
  return get(groupsWithHiddenIgnoredAssets).has(groupId);
}

// Helper to check if a group is currently showing ignored assets
function isShowingIgnoredAssets(groupId: string): boolean {
  return get(groupsShowingIgnoredAssets).has(groupId);
}
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
      :limit="limit"
      :total="total"
      :found="found"
      class="px-2"
      :entries-found-total="entriesFoundTotal"
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
        <template
          v-for="{ data: row, index } in virtualList"
          :key="`${row.type}-${row.groupId}-${index}`"
        >
          <!-- Group Header -->
          <HistoryEventsGroupItem
            v-if="row.type === 'group-header'"
            :group="row.data"
            :group-events="getGroupEvents(row.groupId)"
            :hide-actions="hideActions"
            :loading="eventsLoading"
            :duplicate-handling-status="duplicateHandlingStatus"
            :has-hidden-ignored-assets="hasHiddenIgnoredAssets(row.groupId)"
            :showing-ignored-assets="isShowingIgnoredAssets(row.groupId)"
            :variant="itemVariant"
            @add-event="addEvent($event, row.data)"
            @toggle-ignore="toggle($event)"
            @toggle-show-ignored-assets="toggleShowIgnoredAssets(row.groupId)"
            @redecode="redecode($event, row.data.groupIdentifier)"
            @redecode-with-options="redecodeWithOptions($event, row.data.groupIdentifier)"
            @delete-tx="confirmTxAndEventsDelete($event)"
            @fix-duplicate="emit('refresh')"
          />

          <!-- Event Placeholder -->
          <div
            v-else-if="row.type === 'event-placeholder'"
            class="animate-pulse contain-content"
            :class="isCardLayout ? 'p-3 border-b border-default' : 'h-[72px] flex items-center gap-4 border-b border-default px-4 pl-6'"
          >
            <template v-if="isCardLayout">
              <!-- Top row: Event type with icon -->
              <div class="flex items-center gap-3 mb-2">
                <div class="size-10 rounded-full bg-rui-grey-300 dark:bg-rui-grey-700 shrink-0" />
                <div class="flex flex-col gap-1">
                  <div class="h-4 w-20 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
                  <div class="h-3 w-14 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
                </div>
              </div>
              <!-- Middle row: Asset & Amount -->
              <div class="flex items-center gap-2 mb-2">
                <div class="size-8 rounded-full bg-rui-grey-300 dark:bg-rui-grey-700" />
                <div class="flex flex-col gap-1">
                  <div class="h-4 w-24 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
                  <div class="h-3 w-16 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
                </div>
              </div>
              <!-- Bottom row: Notes -->
              <div class="h-3 w-3/4 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
            </template>
            <template v-else>
              <div class="w-56 shrink-0 flex items-center gap-3">
                <div class="size-10 rounded-full bg-rui-grey-300 dark:bg-rui-grey-700" />
                <div class="flex flex-col gap-1.5">
                  <div class="h-4 w-20 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
                  <div class="h-3 w-14 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
                </div>
              </div>
              <div class="w-56 xl:w-60 shrink-0 flex items-center gap-2">
                <div class="size-8 rounded-full bg-rui-grey-300 dark:bg-rui-grey-700" />
                <div class="flex flex-col gap-1.5">
                  <div class="h-4 w-24 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
                  <div class="h-3 w-16 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
                </div>
              </div>
              <div class="flex-1 min-w-0 flex flex-col gap-1.5">
                <div class="h-3.5 w-3/4 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
                <div class="h-3 w-1/2 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
              </div>
              <div class="w-24 shrink-0" />
            </template>
          </div>

          <!-- Event Detail -->
          <HistoryEventsDetailItem
            v-else-if="row.type === 'event-row'"
            :event="row.data"
            :index="row.index"
            :complete-group-events="getCompleteEventsForItem(row.groupId, row.data)"
            :group-location-label="findGroup(row.groupId)?.locationLabel ?? undefined"
            :hide-actions="hideActions"
            :highlight="isHighlighted(row.data)"
            :highlight-type="getHighlightType(row.data)"
            :selection="selection"
            :variant="itemVariant"
            @edit-event="handleEditEvent($event, row.groupId)"
            @delete-event="confirmDelete($event)"
            @show:missing-rule-action="handleMissingRuleAction($event, row.groupId)"
            @refresh="emit('refresh')"
          />

          <!-- Swap -->
          <HistoryEventsSwapItem
            v-else-if="row.type === 'swap-row'"
            :events="row.events"
            :complete-group-events="getCompleteSubgroupEvents(row.events)"
            :group-location-label="findGroup(row.groupId)?.locationLabel ?? undefined"
            :hide-actions="hideActions"
            :highlight="isSwapHighlighted(row.events)"
            :highlight-type="getSwapHighlightType(row.events)"
            :selection="selection"
            :variant="itemVariant"
            @edit-event="handleEditEvent($event, row.groupId)"
            @delete-event="confirmDelete($event)"
            @show:missing-rule-action="handleMissingRuleAction($event, row.groupId)"
            @refresh="emit('refresh')"
            @toggle-expand="toggleSwapExpanded(row.swapKey)"
          />

          <!-- Swap Collapse -->
          <HistoryEventsSwapCollapseRow
            v-else-if="row.type === 'swap-collapse'"
            :event-count="row.eventCount"
            @collapse="toggleSwapExpanded(row.swapKey)"
          />

          <!-- Matched Movement -->
          <HistoryEventsMatchedMovementItem
            v-else-if="row.type === 'matched-movement-row'"
            :events="row.events"
            :complete-group-events="getCompleteSubgroupEvents(row.events)"
            :group-location-label="findGroup(row.groupId)?.locationLabel ?? undefined"
            :hide-actions="hideActions"
            :highlight="isSwapHighlighted(row.events)"
            :highlight-type="getSwapHighlightType(row.events)"
            :selection="selection"
            :variant="itemVariant"
            @edit-event="handleEditEvent($event, row.groupId)"
            @delete-event="confirmDelete($event)"
            @show:missing-rule-action="handleMissingRuleAction($event, row.groupId)"
            @unlink-event="confirmUnlink($event)"
            @refresh="emit('refresh')"
            @toggle-expand="toggleMovementExpanded(row.movementKey)"
          />

          <!-- Matched Movement Collapse -->
          <HistoryEventsSwapCollapseRow
            v-else-if="row.type === 'matched-movement-collapse'"
            :event-count="row.eventCount"
            :events="getGroupEvents(row.groupId)"
            label-type="movement"
            @unlink-event="unlinkGroup(row.groupId)"
            @collapse="toggleMovementExpanded(row.movementKey)"
          />

          <!-- Load More -->
          <HistoryEventsLoadMoreRow
            v-else-if="row.type === 'load-more'"
            :hidden-count="row.hiddenCount"
            :total-count="row.totalCount"
            @load-more="loadMoreEvents(row.groupId)"
          />
        </template>
      </div>
    </div>
  </div>

  <!-- Redecode Confirmation Dialog -->
  <RedecodeConfirmationDialog
    v-model:show="showRedecodeConfirmation"
    :payload="redecodePayload"
    :has-custom-events="hasCustomEvents"
    :show-indexer-options="showIndexerOptions"
    @confirm="confirmRedecode($event)"
  />
</template>
