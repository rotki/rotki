<script setup lang="ts">
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventsRestrictions } from '@/modules/history/events/history-events-restrictions';
import type { HistoryEventsTableHighlight, HistoryEventsTableSource } from '@/modules/history/events/types';
import type { Filters } from '@/modules/history/events/use-events-filter';
import { AccountingOverlayToggle, BalanceDivergenceToggle } from '@/modules/history/balances/components';
import { OverlayMode } from '@/modules/history/balances/use-accounting-overlay';
import HistoryEventsVirtualTable from '@/modules/history/events/components/HistoryEventsVirtualTable.vue';
import {
  getDefaultToggles,
  useHistoryEventFields,
  useHistoryEventNavigationConsumer,
  useHistoryEventsActions,
  useHistoryEventsDeletion,
  useHistoryEventsDialogRouting,
  useHistoryEventsFilters,
  useHistoryEventsOverlay,
  useHistoryEventsSelectionActions,
  useHistoryEventsSelectionMode,
  useHistoryEventsStatus,
  useHistoryEventsTableHeight,
  useUnmatchedAssetMovements,
  useUnmatchedBridgeTransactions,
} from '@/modules/history/events/composables';
import HistoryEventsDialogContainer from '@/modules/history/events/HistoryEventsDialogContainer.vue';
import HistoryEventsFiltersChips from '@/modules/history/events/HistoryEventsFiltersChips.vue';
import HistoryEventsTableActions from '@/modules/history/events/HistoryEventsTableActions.vue';
import HistoryEventsViewButtons from '@/modules/history/events/HistoryEventsViewButtons.vue';
import {
  EventAssetPriceUpdateDialog,
  type EventPriceUpdatePayload,
  provideEventPriceUpdate,
} from '@/modules/history/events/prices/use-event-price-update-trigger';
import { provideHistoryEventsSelection } from '@/modules/history/events/use-history-events-selection-context';
import { useHistoryEventsViewActions } from '@/modules/history/events/use-history-events-view-actions';
import { toTableSource } from '@/modules/history/events/view-projections';
import RefreshButton from '@/modules/shell/components/RefreshButton.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';

defineOptions({ inheritAttrs: false });

const { mainPage = false, restrictions = {}, sectionTitle = '' } = defineProps<{
  /** What this view fixes for the user. See HistoryEventsRestrictions. */
  restrictions?: HistoryEventsRestrictions;
  sectionTitle?: string;
  mainPage?: boolean;
}>();

const SyncProgressPanel = defineAsyncComponent(() => import('@/modules/shell/sync-progress/components/SyncProgressPanel.vue'));

const { t } = useI18n({ useScope: 'global' });

const toggles = ref<HistoryEventsToggles>(getDefaultToggles());
// Synced through the router query by useHistoryEventsFilters' queryParamsOnly (see below).
const overlayMode = ref<OverlayMode>(OverlayMode.NONE);

const eventPriceUpdatePayload = ref<EventPriceUpdatePayload>();

const dialogContainer = useTemplateRef<InstanceType<typeof HistoryEventsDialogContainer>>('dialogContainer');

const tableHeightOffset = useHistoryEventsTableHeight(
  useTemplateRef<ComponentPublicInstance>('syncProgressPanel'),
  useTemplateRef<ComponentPublicInstance>('tableActions'),
  useTemplateRef<ComponentPublicInstance>('filtersChips'),
);

const {
  anyEventsDecoding,
  processing,
  refreshing,
  sectionLoading,
  shouldFetchEventsRegularly,
} = useHistoryEventsStatus();

const usedTitle = computed<string>(() => sectionTitle || t('transactions.title'));

// The filter bag, and the fields bound to it, in that order: the fields read the bag to scope
// their option lists, and the table below reads the url shape of the bag off the fields.
const modelFilters = ref<Filters>({});
const fields = useHistoryEventFields({ modelFilters, restrictions: () => restrictions });

const {
  clearFilters,
  duplicateHandlingStatus,
  refetch,
  filters,
  groupIdentifiers,
  groupLoading,
  groups,
  hasActiveFilters,
  highlightedGroupIdentifier,
  highlightedIdentifiers,
  highlightTypes,
  identifiers,
  includes,
  action,
  locationLabels,
  onActionChanged,
  onLocationLabelsChanged,
  pagination,
  requestPayload,
  setPage,
  sort,
} = useHistoryEventsFilters({
  fields,
  filters: modelFilters,
  mainPage: () => mainPage,
  restrictions: () => restrictions,
}, toggles, overlayMode);

const { available: overlayAvailable } = useHistoryEventsOverlay(overlayMode, groups);

const actions = useHistoryEventsActions({
  entryTypes: () => restrictions.entryTypes,
  refetch,
  groups,
  mainPage: () => mainPage,
  onlyChains: () => restrictions.onlyChains ?? [],
  shouldFetchEventsRegularly,
});

const selectionMode = useHistoryEventsSelectionMode();

// Read at the leaves (the row checkboxes) rather than threaded through the table and row switch.
provideHistoryEventsSelection(selectionMode);

const tableSource = computed<HistoryEventsTableSource>(() => toTableSource({
  groupLoading: get(groupLoading),
  groups: get(groups),
  identifiers: get(identifiers),
  requestPayload: get(requestPayload),
  toggles: get(toggles),
}));

const tableHighlight = computed<HistoryEventsTableHighlight>(() => ({
  groupIdentifier: get(highlightedGroupIdentifier),
  identifiers: get(highlightedIdentifiers),
  types: get(highlightTypes),
}));

const debouncedProcessing = refDebounced(processing, 200);
const { autoMatchLoading, autoMatchMovement, refreshUnmatchedAssetMovements } = useUnmatchedAssetMovements();
const { autoMatchLoading: bridgeAutoMatchLoading, refreshUnmatchedBridgeTransactions } = useUnmatchedBridgeTransactions();
const backgroundLoading = logicOr(debouncedProcessing, autoMatchLoading, bridgeAutoMatchLoading);

const {
  groupedEventsByTxRef,
  handleBridgeChanged,
  handleMovementChanged,
  handleRedecode,
  handleUpdateEventIds,
  originalGroups,
} = useHistoryEventsViewActions({
  autoMatchMovement,
  backgroundLoading,
  fetchDataAndLocations: async () => actions.fetch.dataAndLocations(),
  fetchDataAndRedecode: async event => actions.fetch.dataAndRedecode(event),
  groups,
  refreshAll: async () => actions.refresh.all(),
  refreshUnmatchedAssetMovements,
  refreshUnmatchedBridgeTransactions,
  setAvailableIds: ids => selectionMode.setAvailableIds(ids),
  setTotalMatchingCount: count => selectionMode.setTotalMatchingCount(count),
});

const deletion = useHistoryEventsDeletion(
  selectionMode,
  groupedEventsByTxRef,
  originalGroups,
  () => actions.fetch.dataAndLocations(),
  requestPayload,
);

const {
  modelAccountingRuleToEdit,
  handleAccountingRuleRefresh,
  handleSelectionAction,
  ignoreStatus,
  selectedEventIds,
} = useHistoryEventsSelectionActions({
  deletion,
  originalGroups,
  refreshCallback: () => actions.fetch.dataAndLocations(),
  selectionMode,
});

useHistoryEventNavigationConsumer(pagination, requestPayload, groupLoading);

provideEventPriceUpdate({
  open: (payload) => {
    set(eventPriceUpdatePayload, payload);
  },
});

useHistoryEventsDialogRouting(dialogContainer);
</script>

<template>
  <div>
    <SyncProgressPanel
      v-if="mainPage"
      ref="syncProgressPanel"
      class="-mt-4 mb-4"
    />
    <TablePageLayout
      :hide-header="!mainPage"
      :child="!mainPage"
      :title="[t('navigation_menu.history'), usedTitle]"
      v-bind="$attrs"
    >
      <template #buttons>
        <HistoryEventsViewButtons
          :processing="processing"
          :loading="anyEventsDecoding"
          :include-evm-events="includes.evmEvents"
          @refresh="actions.refresh.all(true, $event)"
          @show:dialog="dialogContainer?.show($event)"
        />
      </template>

      <div>
        <div class="flex gap-4 items-start">
          <RuiCard class="flex-1 min-w-0">
            <template
              v-if="!mainPage"
              #header
            >
              <div class="flex items-center gap-x-1">
                <RefreshButton
                  :disabled="refreshing"
                  :tooltip="t('transactions.refresh_tooltip')"
                  @refresh="actions.refresh.all(true)"
                />
                {{ usedTitle }}
              </div>
            </template>

            <HistoryEventsTableActions
              ref="tableActions"
              v-model:filters="filters"
              v-model:toggles="toggles"
              :action="action"
              :location-labels="locationLabels"
              :processing="processing"
              :fields="fields"
              :export-params="requestPayload"
              :hide-redecode-buttons="!mainPage"
              :selection="selectionMode.state.value"
              :ignore-status="ignoreStatus"
              @update:action="onActionChanged($event)"
              @update:location-labels="onLocationLabelsChanged($event)"
              @redecode="actions.redecode.by($event)"
              @selection:action="handleSelectionAction($event)"
            />

            <div
              v-if="overlayAvailable"
              class="flex items-center justify-end gap-2 px-2 pt-2 mb-1"
            >
              <AccountingOverlayToggle v-model="overlayMode" />
              <BalanceDivergenceToggle />
            </div>

            <HistoryEventsFiltersChips
              ref="filtersChips"
              :group-identifiers="groupIdentifiers"
              :duplicate-handling-status="duplicateHandlingStatus"
              @refresh="actions.fetch.dataAndLocations()"
            />

            <HistoryEventsVirtualTable
              v-model:sort="sort"
              v-model:pagination="pagination"
              :table-height-offset="tableHeightOffset"
              :processing="processing || refreshing"
              :source="tableSource"
              :highlight="tableHighlight"
              :has-active-filters="hasActiveFilters"
              :duplicate-handling-status="duplicateHandlingStatus"
              @clear-filters="clearFilters()"
              @show:dialog="dialogContainer?.show($event)"
              @refresh="handleRedecode($event)"
              @refresh:block-event="actions.redecode.blocks($event)"
              @set-page="setPage($event)"
              @update-event-ids="handleUpdateEventIds($event)"
            />
          </RuiCard>
        </div>

        <HistoryEventsDialogContainer
          ref="dialogContainer"
          v-model:accounting-rule-to-edit="modelAccountingRuleToEdit"
          :loading="processing"
          :refreshing="refreshing"
          :section-loading="sectionLoading"
          :event-handlers="actions.dialogHandlers"
          :selected-event-ids="selectedEventIds"
          @accounting-rule-refresh="handleAccountingRuleRefresh()"
          @bridge-matched="handleBridgeChanged()"
          @movement-matched="handleMovementChanged()"
        />

        <EventAssetPriceUpdateDialog
          v-if="eventPriceUpdatePayload"
          v-model="eventPriceUpdatePayload"
        />
      </div>
    </TablePageLayout>
  </div>
</template>
