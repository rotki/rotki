<script setup lang="ts">
import type { Account, Blockchain, HistoryEventEntryType } from '@rotki/common';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { get, set } from '@vueuse/shared';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import { DIALOG_TYPES, type HistoryEventsToggles } from '@/components/history/events/dialog-types';
import HistoryEventsDialogContainer from '@/components/history/events/HistoryEventsDialogContainer.vue';
import HistoryEventsFiltersChips from '@/components/history/events/HistoryEventsFiltersChips.vue';
import HistoryEventsTableActions from '@/components/history/events/HistoryEventsTableActions.vue';
import HistoryEventsViewButtons from '@/components/history/events/HistoryEventsViewButtons.vue';
import HistoryQueryStatus from '@/components/history/events/HistoryQueryStatus.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { HISTORY_EVENT_ACTIONS, type HistoryEventAction } from '@/composables/history/events/types';
import { useHistoryEventsActions } from '@/composables/history/events/use-history-events-actions';
import { useHistoryEventsFilters } from '@/composables/history/events/use-history-events-filters';
import HistoryEventsTable from '@/modules/history/events/components/HistoryEventsTable.vue';
import { useHistoryEventsDeletion } from '@/modules/history/events/composables/use-history-events-deletion';
import { useHistoryEventsSelectionActions } from '@/modules/history/events/composables/use-history-events-selection-actions';
import { useHistoryEventsSelectionMode } from '@/modules/history/events/composables/use-selection-mode';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';

type Period = { fromTimestamp?: string; toTimestamp?: string } | { fromTimestamp?: number; toTimestamp?: number };

const props = withDefaults(defineProps<{
  location?: string;
  protocols?: string[];
  eventTypes?: string[];
  eventSubTypes?: string[];
  entryTypes?: HistoryEventEntryType[];
  period?: Period;
  validators?: number[];
  externalAccountFilter?: Account[];
  useExternalAccountFilter?: boolean;
  sectionTitle?: string;
  mainPage?: boolean;
  onlyChains?: Blockchain[];
}>(), {
  entryTypes: undefined,
  eventSubTypes: () => [],
  eventTypes: () => [],
  externalAccountFilter: () => [],
  location: undefined,
  mainPage: false,
  onlyChains: () => [],
  period: undefined,
  protocols: () => [],
  sectionTitle: '',
  useExternalAccountFilter: undefined,
  validators: undefined,
});

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const {
  entryTypes,
  eventSubTypes,
  eventTypes,
  externalAccountFilter,
  location,
  mainPage,
  onlyChains,
  period,
  protocols,
  sectionTitle,
  useExternalAccountFilter,
  validators,
} = toRefs(props);

const toggles = ref<HistoryEventsToggles>({
  customizedEventsOnly: false,
  matchExactEvents: false,
  showIgnoredAssets: false,
});

const currentAction = ref<HistoryEventAction>(HISTORY_EVENT_ACTIONS.QUERY);

const dialogContainer = useTemplateRef<InstanceType<typeof HistoryEventsDialogContainer>>('dialogContainer');

const {
  anyEventsDecoding,
  processing,
  refreshing,
  sectionLoading,
  shouldFetchEventsRegularly,
} = useHistoryEventsStatus();

const usedTitle = computed<string>(() => get(sectionTitle) || t('transactions.title'));

const {
  fetchData,
  filters,
  groupLoading,
  groups,
  highlightedIdentifiers,
  identifiers,
  includes,
  locationLabels,
  locations,
  matchers,
  onLocationLabelsChanged,
  pageParams,
  pagination,
  setPage,
  sort,
} = useHistoryEventsFilters(
  {
    entryTypes,
    eventSubTypes,
    eventTypes,
    externalAccountFilter,
    location,
    mainPage,
    period,
    protocols,
    useExternalAccountFilter,
    validators,
  },
  toggles,
);

const actions = useHistoryEventsActions({
  currentAction,
  entryTypes,
  fetchData,
  groups,
  onlyChains,
  shouldFetchEventsRegularly,
});

const selectionMode = useHistoryEventsSelectionMode();

// Store grouped events for checking complete EVM transactions
const groupedEventsByTxHash = ref<Record<string, HistoryEventRow[]>>({});
// Store original groups data to preserve swap groups
const originalGroups = ref<HistoryEventRow[]>([]);

const deletion = useHistoryEventsDeletion(
  selectionMode,
  groupedEventsByTxHash,
  originalGroups,
  () => actions.fetch.dataAndLocations(),
);

const {
  accountingRuleToEdit,
  handleAccountingRuleRefresh,
  handleSelectionAction,
  selectedEventIds,
} = useHistoryEventsSelectionActions({
  deletion,
  originalGroups,
  selectionMode,
});

// Handle updating available event IDs from the table
function handleUpdateEventIds({ eventIds, groupedEvents, rawEvents }: { eventIds: number[]; groupedEvents: Record<string, HistoryEventRow[]>; rawEvents?: HistoryEventRow[] }): void {
  // Create mock event entries with just the identifiers
  const events: HistoryEventEntry[] = eventIds.map(id => ({ identifier: id } as HistoryEventEntry));
  selectionMode.setAvailableIds(events);

  // Store the grouped events for checking complete transactions
  set(groupedEventsByTxHash, groupedEvents);
  // Store the original groups data - prefer rawEvents if available, otherwise use groups.data
  set(originalGroups, rawEvents || get(groups).data);
}

watchImmediate(route, async (route) => {
  if (!route.query.openDecodingStatusDialog) {
    return;
  }
  await nextTick();
  get(dialogContainer)?.show({ type: DIALOG_TYPES.DECODING_STATUS });
  await router.replace({ query: {} });
});

watch(processing, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await actions.fetch.dataAndLocations();
});

// Wait until the route doesn't change anymore to give time for the persisted filter to be set.
watchDebounced(route, async () => {
  await actions.refresh.all();
}, { debounce: 500, immediate: true, once: true });
</script>

<template>
  <TablePageLayout
    :hide-header="!mainPage"
    :child="!mainPage"
    :title="[t('navigation_menu.history'), usedTitle]"
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
      <RuiCard>
        <template
          v-if="!mainPage"
          #header
        >
          <CardTitle>
            <RefreshButton
              :disabled="refreshing"
              :tooltip="t('transactions.refresh_tooltip')"
              @refresh="actions.refresh.all(true)"
            />
            {{ usedTitle }}
          </CardTitle>
        </template>

        <HistoryEventsTableActions
          v-model:filters="filters"
          v-model:toggles="toggles"
          :location-labels="locationLabels"
          :processing="processing"
          :matchers="matchers"
          :export-params="pageParams"
          :hide-redecode-buttons="!mainPage"
          :hide-account-selector="useExternalAccountFilter"
          :selection="selectionMode.state.value"
          @update:location-labels="onLocationLabelsChanged($event)"
          @redecode="actions.redecode.by($event)"
          @selection:action="handleSelectionAction($event)"
        />

        <HistoryEventsFiltersChips />

        <HistoryEventsTable
          v-model:sort="sort"
          v-model:pagination="pagination"
          :group-loading="groupLoading"
          :groups="groups"
          :page-params="toggles.matchExactEvents ? pageParams : undefined"
          :exclude-ignored="!toggles.showIgnoredAssets"
          :identifiers="identifiers"
          :highlighted-identifiers="highlightedIdentifiers"
          :selection="selectionMode"
          @show:dialog="dialogContainer?.show($event)"
          @refresh="actions.fetch.dataAndRedecode($event)"
          @refresh:block-event="actions.redecode.blocks($event)"
          @set-page="setPage($event)"
          @update-event-ids="handleUpdateEventIds($event)"
        >
          <template #query-status="{ colspan }">
            <HistoryQueryStatus
              v-model:current-action="currentAction"
              :only-chains="onlyChains"
              :locations="locations"
              :colspan="colspan"
              :loading="processing"
              @show:dialog="dialogContainer?.show($event)"
            />
          </template>
        </HistoryEventsTable>
      </RuiCard>

      <HistoryEventsDialogContainer
        ref="dialogContainer"
        v-model:accounting-rule-to-edit="accountingRuleToEdit"
        :loading="processing"
        :refreshing="refreshing"
        :section-loading="sectionLoading"
        :event-handlers="actions.dialogHandlers"
        :selected-event-ids="selectedEventIds"
        @accounting-rule-refresh="handleAccountingRuleRefresh()"
      />
    </div>
  </TablePageLayout>
</template>
