<script setup lang="ts">
import type { Account, Blockchain, HistoryEventEntryType } from '@rotki/common';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { get } from '@vueuse/shared';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import AccountingRuleFormDialog from '@/components/settings/accounting/rule/AccountingRuleFormDialog.vue';
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

// Accounting rule dialog state
const accountingRuleToEdit = ref<AccountingRuleEntry | undefined>();
const selectedEventIds = ref<number[]>([]);

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

const deletion = useHistoryEventsDeletion(
  selectionMode,
  groupedEventsByTxHash,
  groups,
  () => actions.fetch.dataAndLocations(),
);

// Handle updating available event IDs from the table
function handleUpdateEventIds({ eventIds, groupedEvents }: { eventIds: number[]; groupedEvents: Record<string, HistoryEventRow[]> }): void {
  // Create mock event entries with just the identifiers
  const events: HistoryEventEntry[] = eventIds.map(id => ({ identifier: id } as HistoryEventEntry));
  selectionMode.setAvailableIds(events);

  // Store the grouped events for checking complete transactions
  set(groupedEventsByTxHash, groupedEvents);
}

// Handle accounting rule refresh
function handleAccountingRuleRefresh(): void {
  // Exit selection mode after successfully creating a rule
  selectionMode.actions.exit();
}

// Handle selection-related actions
async function handleSelectionAction(action: string): Promise<void> {
  switch (action) {
    case 'delete':
      await deletion.deleteSelected();
      break;
    case 'create-rule':
      // Gather selected event IDs and open the accounting rule dialog
      const selectedIds = Array.from(selectionMode.state.value.selectedIds);
      set(selectedEventIds, selectedIds);
      // Initialize with an empty rule
      set(accountingRuleToEdit, {
        accountingTreatment: null,
        countCostBasisPnl: { value: false },
        countEntireAmountSpend: { value: false },
        counterparty: null,
        eventSubtype: '',
        eventType: '',
        identifier: 0,
        taxable: { value: false },
      });
      break;
    case 'toggle-mode':
      selectionMode.actions.toggle();
      break;
    case 'exit':
      selectionMode.actions.exit();
      break;
    case 'toggle-all':
      selectionMode.actions.toggleAll();
      break;
  }
}

watchImmediate(route, async (route) => {
  if (!route.query.openDecodingStatusDialog) {
    return;
  }
  await nextTick();
  get(dialogContainer)?.show({ type: DIALOG_TYPES.DECODING_STATUS });
  await router.replace({ query: {} });
});

watch(anyEventsDecoding, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await actions.fetch.dataAndLocations();
});

onMounted(async () => {
  await actions.refresh.all();
});
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
        :loading="processing"
        :refreshing="refreshing"
        :section-loading="sectionLoading"
        :event-handlers="actions.dialogHandlers"
      />

      <AccountingRuleFormDialog
        v-model="accountingRuleToEdit"
        :event-ids="selectedEventIds"
        @refresh="handleAccountingRuleRefresh()"
      />
    </div>
  </TablePageLayout>
</template>
