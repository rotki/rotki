<script setup lang="ts">
import type { HistoryEventsToggles } from '@/modules/history/events/dialog-types';
import type { HistoryEventsRestrictions } from '@/modules/history/events/history-events-restrictions';
import type { HistoryEventsTableHighlight, HistoryEventsTableSource } from '@/modules/history/events/types';
import type { Filters } from '@/modules/history/events/use-events-filter';
import AccountingOverlayToggle from '@/modules/history/balances/AccountingOverlayToggle.vue';
import BalanceDivergenceToggle from '@/modules/history/balances/BalanceDivergenceToggle.vue';
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
import { useHistoryEventsSection } from '@/modules/history/events/use-history-events-section';
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

defineSlots<{
  /** Replaces the heading above the frame when embedded, e.g. to set actions beside the title. */
  title?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const toggles = ref<HistoryEventsToggles>(getDefaultToggles());
// Synced through the router query by useHistoryEventsFilters' queryParamsOnly (see below).
const overlayMode = ref<OverlayMode>(OverlayMode.NONE);

const eventPriceUpdatePayload = ref<EventPriceUpdatePayload>();

const dialogContainer = useTemplateRef<InstanceType<typeof HistoryEventsDialogContainer>>('dialogContainer');

const tableHeightOffset = useHistoryEventsTableHeight(
  useTemplateRef<ComponentPublicInstance>('tableActions'),
  useTemplateRef<HTMLDivElement>('contextStrip'),
);

const {
  anyEventsDecoding,
  processing,
  refreshing,
  sectionLoading,
  shouldFetchEventsRegularly,
} = useHistoryEventsStatus();

const usedTitle = computed<string>(() => sectionTitle || t('transactions.title'));

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

const { autoMatchLoading, autoMatchMovement, refreshUnmatchedAssetMovements } = useUnmatchedAssetMovements();
const { autoMatchLoading: bridgeAutoMatchLoading, refreshUnmatchedBridgeTransactions } = useUnmatchedBridgeTransactions();
const autoMatching = logicOr(autoMatchLoading, bridgeAutoMatchLoading);

const {
  groupedEventsByTxRef,
  handleBridgeChanged,
  handleMovementChanged,
  handleRedecode,
  handleUpdateEventIds,
  originalGroups,
} = useHistoryEventsViewActions({
  autoMatching,
  autoMatchMovement,
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

const section = useHistoryEventsSection();

// A page showing the events as one of its sections refreshes them with the rest of the page.
if (section)
  watch(section.reloads, async () => actions.fetch.dataAndLocations());
</script>

<template>
  <div>
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
          @redecode="actions.redecode.by($event)"
          @refresh="actions.refresh.all(true, $event)"
          @show:dialog="dialogContainer?.show($event)"
        />
      </template>

      <div>
        <div class="flex gap-4 items-start">
          <section
            class="flex-1 min-w-0"
            data-testid="history-events-container"
          >
            <div
              v-if="!mainPage"
              class="flex items-center gap-x-1 mb-3 min-h-8"
            >
              <slot name="title">
                <RefreshButton
                  v-if="!section"
                  :disabled="refreshing"
                  :tooltip="t('transactions.refresh_tooltip')"
                  @refresh="actions.refresh.all(true)"
                />
                <h3 class="text-base font-semibold text-rui-text m-0">
                  {{ usedTitle }}
                </h3>
              </slot>
            </div>

            <div class="border border-rui-divider rounded-rui-card overflow-hidden bg-rui-surface">
              <HistoryEventsTableActions
                ref="tableActions"
                v-model:filters="filters"
                v-model:toggles="toggles"
                class="mb-0! p-3 border-b border-rui-divider"
                :action="action"
                :location-labels="locationLabels"
                :fields="fields"
                :export-params="requestPayload"
                :selection="selectionMode.state.value"
                :ignore-status="ignoreStatus"
                @update:action="onActionChanged($event)"
                @update:location-labels="onLocationLabelsChanged($event)"
                @selection:action="handleSelectionAction($event)"
              />

              <div
                ref="contextStrip"
                class="flex flex-wrap items-start gap-2 px-3 py-2 empty:hidden"
              >
                <HistoryEventsFiltersChips
                  class="mr-auto"
                  :group-identifiers="groupIdentifiers"
                  :duplicate-handling-status="duplicateHandlingStatus"
                  @refresh="actions.fetch.dataAndLocations()"
                />
                <AccountingOverlayToggle
                  v-if="overlayAvailable"
                  v-model="overlayMode"
                  class="ml-auto"
                />
                <BalanceDivergenceToggle v-if="overlayAvailable" />
              </div>

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
                @refetch="refetch()"
                @set-page="setPage($event)"
                @update-event-ids="handleUpdateEventIds($event)"
              />
            </div>
          </section>
        </div>

        <HistoryEventsDialogContainer
          ref="dialogContainer"
          v-model:accounting-rule-to-edit="modelAccountingRuleToEdit"
          :loading="processing"
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
