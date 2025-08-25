<script setup lang="ts">
import type { Account, Blockchain, HistoryEventEntryType } from '@rotki/common';
import MissingRulesDialog from '@/components/dialogs/MissingRulesDialog.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import HistoryEventFormDialog from '@/components/history/events/HistoryEventFormDialog.vue';
import HistoryEventsDecodingStatus from '@/components/history/events/HistoryEventsDecodingStatus.vue';
import HistoryEventsProtocolCacheUpdateStatus
  from '@/components/history/events/HistoryEventsProtocolCacheUpdateStatus.vue';
import HistoryEventsTableActions from '@/components/history/events/HistoryEventsTableActions.vue';
import HistoryEventsViewButtons from '@/components/history/events/HistoryEventsViewButtons.vue';
import HistoryQueryStatus from '@/components/history/events/HistoryQueryStatus.vue';
import RepullingTransactionFormDialog from '@/components/history/events/tx/RepullingTransactionFormDialog.vue';
import TransactionFormDialog from '@/components/history/events/tx/TransactionFormDialog.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { useHistoryEventsActions } from '@/composables/history/events/use-history-events-actions';
import { useHistoryEventsDialogs } from '@/composables/history/events/use-history-events-dialogs';
import { useHistoryEventsFilters } from '@/composables/history/events/use-history-events-filters';
import HistoryEventsTable from '@/modules/history/events/components/HistoryEventsTable.vue';
import { useHistoryEventsAutoFetch } from '@/modules/history/events/use-history-events-auto-fetch';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryStore } from '@/store/history';

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

const toggles = ref<{
  customizedEventsOnly: boolean;
  showIgnoredAssets: boolean;
  matchExactEvents: boolean;
}>({
  customizedEventsOnly: false,
  matchExactEvents: false,
  showIgnoredAssets: false,
});
const currentAction = ref<'decode' | 'query'>('query');

const { fetchAssociatedLocations, resetUndecodedTransactionsStatus } = useHistoryStore();
const { decodingStatus } = storeToRefs(useHistoryStore());
const {
  anyEventsDecoding,
  processing,
  refreshing,
  sectionLoading,
  shouldFetchEventsRegularly,
} = useHistoryEventsStatus();

const usedTitle = computed<string>(() => get(sectionTitle) || t('transactions.title'));

const {
  accounts,
  fetchData,
  filters,
  groupLoading,
  groups,
  highlightedIdentifiers,
  identifiers,
  includes,
  locations,
  matchers,
  onFilterAccountsChanged,
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
  fetchDataAndLocations,
);

const {
  addTransactionModelValue,
  addTxHash,
  decodingStatusDialogOpen,
  decodingStatusDialogPersistent,
  editMissingRulesEntry,
  formData,
  missingRuleData,
  onAddMissingRule,
  onShowDialog,
  protocolCacheStatusDialogOpen,
  showForm,
  showRePullTransactionsDialog,
} = useHistoryEventsDialogs();

const {
  fetchAndRedecodeEvents,
  forceRedecodeEvmEvents,
  redecode,
  redecodeAllEvents,
  redecodeBlockEvents,
  refresh,
  refreshTransactions,
} = useHistoryEventsActions({
  currentAction,
  decodingStatusDialogPersistent,
  entryTypes,
  fetchAssociatedLocations,
  fetchData,
  groups,
  onlyChains,
});

useHistoryEventsAutoFetch(shouldFetchEventsRegularly, fetchDataAndLocations);

async function fetchDataAndLocations(): Promise<void> {
  await fetchData();
  await fetchAssociatedLocations();
}

function removeIdentifierParam() {
  const query = { ...route.query };
  delete query.identifiers;
  router.push({ query });
}

function removeEventIdentifierParam() {
  const query = { ...route.query };
  delete query.eventIdentifiers;
  delete query.highlightIdentifier;
  router.push({ query });
}

watchImmediate(route, async (route) => {
  if (route.query.openDecodingStatusDialog) {
    set(decodingStatusDialogOpen, true);
    await router.replace({ query: {} });
  }
});

watch(anyEventsDecoding, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchDataAndLocations();
});

onMounted(async () => {
  await refresh();
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
        v-model:open-decoding-dialog="decodingStatusDialogOpen"
        :processing="processing"
        :loading="anyEventsDecoding"
        :include-evm-events="includes.evmEvents"
        @refresh="refresh(true, $event)"
        @show:form="showForm($event)"
        @show:add-transaction-form="addTxHash()"
        @show:repulling-transactions-form="showRePullTransactionsDialog = true"
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
              @refresh="refresh(true)"
            />
            {{ usedTitle }}
          </CardTitle>
        </template>

        <HistoryEventsTableActions
          v-model:filters="filters"
          v-model:toggles="toggles"
          :accounts="accounts"
          :processing="processing"
          :matchers="matchers"
          :export-params="pageParams"
          :hide-redecode-buttons="!mainPage"
          :hide-account-selector="useExternalAccountFilter"
          @update:accounts="onFilterAccountsChanged($event)"
          @redecode="redecode($event)"
        />

        <div
          v-if="route.query.identifiers"
          class="mb-4"
        >
          <RuiChip
            closeable
            color="primary"
            size="sm"
            variant="outlined"
            @click:close="removeIdentifierParam()"
          >
            {{ t('transactions.events.show_missing_acquisition') }}
          </RuiChip>
        </div>

        <div
          v-if="route.query.eventIdentifiers"
          class="mb-4"
        >
          <RuiChip
            closeable
            color="primary"
            size="sm"
            variant="outlined"
            @click:close="removeEventIdentifierParam()"
          >
            {{ t('transactions.events.show_negative_balance') }}
          </RuiChip>
        </div>
        <HistoryEventsTable
          v-model:sort="sort"
          v-model:pagination="pagination"
          :group-loading="groupLoading"
          :groups="groups"
          :page-params="toggles.matchExactEvents ? pageParams : undefined"
          :exclude-ignored="!toggles.showIgnoredAssets"
          :identifiers="identifiers"
          :highlighted-identifiers="highlightedIdentifiers"
          @show:form="showForm($event)"
          @refresh="fetchAndRedecodeEvents($event)"
          @refresh:block-event="redecodeBlockEvents($event)"
          @set-page="setPage($event)"
        >
          <template #query-status="{ colspan }">
            <HistoryQueryStatus
              v-model:current-action="currentAction"
              :only-chains="onlyChains"
              :locations="locations"
              :decoding-status="decodingStatus"
              :colspan="colspan"
              :loading="processing"
              @show:dialog="onShowDialog($event)"
            />
          </template>
        </HistoryEventsTable>

        <HistoryEventFormDialog
          v-model="formData"
          @refresh="fetchAndRedecodeEvents()"
        />

        <TransactionFormDialog
          v-model="addTransactionModelValue"
          :loading="sectionLoading"
          @reload="fetchAndRedecodeEvents({ transactions: [$event] })"
        />

        <RepullingTransactionFormDialog
          v-model="showRePullTransactionsDialog"
          :loading="sectionLoading"
          @refresh="refreshTransactions({
            chains: $event,
            disableEvmEvents: false,
            payload: undefined,
            userInitiated: true,
          });"
        />

        <MissingRulesDialog
          v-model="missingRuleData"
          @edit-event="editMissingRulesEntry($event)"
          @redecode="forceRedecodeEvmEvents({ transactions: [$event] })"
          @add="onAddMissingRule($event)"
          @dismiss="missingRuleData = undefined"
        />
      </RuiCard>

      <RuiDialog
        v-model="decodingStatusDialogOpen"
        max-width="600"
        :persistent="decodingStatusDialogPersistent"
      >
        <HistoryEventsDecodingStatus
          v-if="decodingStatusDialogOpen"
          :refreshing="refreshing"
          :decoding-status="decodingStatus"
          @redecode-all-events="redecodeAllEvents()"
          @reset-undecoded-transactions="resetUndecodedTransactionsStatus()"
        >
          <RuiButton
            variant="text"
            icon
            @click="decodingStatusDialogOpen = false"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </HistoryEventsDecodingStatus>
      </RuiDialog>

      <RuiDialog
        v-model="protocolCacheStatusDialogOpen"
        max-width="600"
      >
        <HistoryEventsProtocolCacheUpdateStatus
          v-if="protocolCacheStatusDialogOpen"
          :refreshing="refreshing"
        >
          <RuiButton
            variant="text"
            icon
            @click="protocolCacheStatusDialogOpen = false"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </HistoryEventsProtocolCacheUpdateStatus>
      </RuiDialog>
    </div>
  </TablePageLayout>
</template>
