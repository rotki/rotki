<script setup lang="ts">
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type {
  AddTransactionHashPayload,
  EventData,
  HistoryEvent,
  HistoryEventEntry,
  HistoryEventRequestPayload,
  PullEvmTransactionPayload,
  RepullingTransactionPayload,
  ShowEventHistoryForm,
} from '@/types/history/events';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import MissingRulesDialog from '@/components/dialogs/MissingRulesDialog.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import HistoryEventFormDialog from '@/components/history/events/HistoryEventFormDialog.vue';
import HistoryEventsDecodingStatus from '@/components/history/events/HistoryEventsDecodingStatus.vue';
import HistoryEventsProtocolCacheUpdateStatus
  from '@/components/history/events/HistoryEventsProtocolCacheUpdateStatus.vue';
import HistoryEventsTable from '@/components/history/events/HistoryEventsTable.vue';
import HistoryEventsTableActions from '@/components/history/events/HistoryEventsTableActions.vue';
import HistoryEventsViewButtons from '@/components/history/events/HistoryEventsViewButtons.vue';
import HistoryQueryStatus from '@/components/history/events/HistoryQueryStatus.vue';
import RepullingTransactionFormDialog from '@/components/history/events/tx/RepullingTransactionFormDialog.vue';
import TransactionFormDialog from '@/components/history/events/tx/TransactionFormDialog.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { type Filters, type Matcher, useHistoryEventFilter } from '@/composables/filters/events';
import { useHistoryEvents } from '@/composables/history/events';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useConfirmStore } from '@/store/confirm';
import { useHistoryStore } from '@/store/history';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { RouterAccountsSchema } from '@/types/route';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { getAccountAddress } from '@/utils/blockchain/accounts/utils';
import { toEvmChainAndTxHash } from '@/utils/history';
import { isEvmEvent, isEvmEventType, isOnlineHistoryEventType } from '@/utils/history/events';
import { type Account, type Blockchain, HistoryEventEntryType, toSnakeCase, type Writeable } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { not } from '@vueuse/math';
import { isEqual } from 'es-toolkit';

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

const { t } = useI18n();
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

const formData = ref<EventData>();
const selectedGroupHeader = ref<HistoryEvent>();
const eventWithMissingRules = ref<HistoryEventEntry>();
const accounts = ref<BlockchainAccount<AddressData>[]>([]);
const locationOverview = ref(get(location));
const toggles = ref<{ customizedEventsOnly: boolean; showIgnoredAssets: boolean }>({
  customizedEventsOnly: false,
  showIgnoredAssets: false,
});
const decodingStatusDialogPersistent = ref<boolean>(false);
const decodingStatusDialogOpen = ref<boolean>(false);
const protocolCacheStatusDialogOpen = ref<boolean>(false);
const currentAction = ref<'decode' | 'query'>('query');

const addTransactionModelValue = ref<AddTransactionHashPayload>();
const repullingTransactionModelValue = ref<RepullingTransactionPayload>();

const { useIsTaskRunning } = useTaskStore();
const { show } = useConfirmStore();
const { fetchAssociatedLocations, resetUndecodedTransactionsStatus } = useHistoryStore();
const { decodingStatus } = storeToRefs(useHistoryStore());
const { getAccountByAddress } = useBlockchainAccountsStore();
const { isAllFinished: isQueryingTxsFinished } = toRefs(useTxQueryStatusStore());
const { isAllFinished: isQueryingOnlineEventsFinished } = toRefs(useEventsQueryStatusStore());
const { isLoading: isSectionLoading } = useStatusStore();

const { fetchHistoryEvents } = useHistoryEvents();

const { refreshTransactions } = useHistoryTransactions();
const { fetchUndecodedTransactionsStatus, pullAndRedecodeTransactions, redecodeTransactions } = useHistoryTransactionDecoding();
const historyEventMappings = useHistoryEventMappings();

const sectionLoading = isSectionLoading(Section.HISTORY_EVENT);
const eventTaskLoading = useIsTaskRunning(TaskType.TRANSACTIONS_DECODING);
const protocolCacheUpdatesLoading = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
const onlineHistoryEventsLoading = useIsTaskRunning(TaskType.QUERY_ONLINE_EVENTS);
const isTransactionsLoading = useIsTaskRunning(TaskType.TX);

const refreshing = logicOr(sectionLoading, eventTaskLoading, onlineHistoryEventsLoading, protocolCacheUpdatesLoading);
const querying = not(logicOr(isQueryingTxsFinished, isQueryingOnlineEventsFinished));
const shouldFetchEventsRegularly = logicOr(querying, refreshing);
const processing = logicOr(isTransactionsLoading, querying, refreshing);

const usedTitle = computed<string>(() => get(sectionTitle) || t('transactions.title'));

const usedAccounts = computed<Account[]>(() => {
  if (isDefined(useExternalAccountFilter))
    return get(externalAccountFilter);

  const accountData = get(accounts).map(account => ({
    address: getAccountAddress(account),
    chain: account.chain,
  }));
  return accountData.length > 0 ? [accountData[0]] : accountData;
});

const includes = computed<{ evmEvents: boolean; onlineEvents: boolean }>(() => {
  const entryTypes = props.entryTypes;
  return {
    evmEvents: entryTypes ? entryTypes.some(type => isEvmEventType(type)) : true,
    onlineEvents: entryTypes ? entryTypes.some(type => isOnlineHistoryEventType(type)) : true,
  };
});

const identifiers = computed<string[] | undefined>(() => {
  const { identifiers } = get(route).query;

  return identifiers ? [identifiers as string] : undefined;
});

const eventIdentifiers = computed<string[] | undefined>(() => {
  const { eventIdentifiers } = get(route).query;

  return eventIdentifiers ? [eventIdentifiers as string] : undefined;
});

const highlightedIdentifiers = computed<string[] | undefined>(() => {
  const { highlightedIdentifier } = get(route).query;

  return highlightedIdentifier ? [highlightedIdentifier as string] : undefined;
});

const {
  fetchData,
  filters,
  isLoading: groupLoading,
  matchers,
  pageParams,
  pagination,
  setPage,
  sort,
  state: groups,
  updateFilter,
  userAction,
} = usePaginationFilters<
  HistoryEventEntry,
  HistoryEventRequestPayload,
  Filters,
  Matcher
>(fetchHistoryEvents, {
  defaultParams: computed(() => {
    if (isDefined(entryTypes)) {
      return {
        entryTypes: {
          values: get(entryTypes),
        },
      };
    }
    return {};
  }),
  extraParams: computed(() => ({
    accounts: get(usedAccounts).map(account => `${account.address}#${account.chain}`),
    customizedEventsOnly: get(toggles, 'customizedEventsOnly'),
    eventIdentifiers: get(eventIdentifiers),
    excludeIgnoredAssets: !get(toggles, 'showIgnoredAssets'),
    identifiers: get(identifiers),
  })),
  filterSchema: () => useHistoryEventFilter({
    eventSubtypes: get(eventSubTypes).length > 0,
    eventTypes: get(eventTypes).length > 0,
    locations: !!get(location),
    period: !!get(period),
    protocols: get(protocols).length > 0,
    validators: !!get(validators),
  }, entryTypes),
  history: get(mainPage) ? 'router' : false,
  onUpdateFilters(query) {
    const parsedAccounts = RouterAccountsSchema.parse(query);
    const accountsParsed = parsedAccounts.accounts;
    if (!accountsParsed || accountsParsed.length === 0)
      set(accounts, []);
    else
      set(accounts, accountsParsed.map(({ address, chain }) => getAccountByAddress(address, chain)));
  },
  requestParams: computed<Partial<HistoryEventRequestPayload>>(() => {
    const params: Writeable<Partial<HistoryEventRequestPayload>> = {
      counterparties: get(protocols),
      eventSubtypes: get(eventSubTypes),
      eventTypes: get(eventTypes),
      groupByEventIds: true,
    };

    const accounts = get(usedAccounts);

    if (isDefined(locationOverview))
      params.location = toSnakeCase(get(locationOverview));

    if (accounts.length > 0)
      params.locationLabels = accounts.map(account => account.address);

    if (isDefined(period)) {
      const { fromTimestamp, toTimestamp } = get(period);
      params.fromTimestamp = fromTimestamp;
      params.toTimestamp = toTimestamp;
    }

    if (isDefined(validators))
      params.validatorIndices = get(validators).map(v => v.toString());

    return params;
  }),
});

async function fetchDataAndLocations(): Promise<void> {
  await fetchData();
  await fetchAssociatedLocations();
}

const locations = computed<string[]>(() => {
  const filteredData = get(filters);

  if ('location' in filteredData) {
    if (typeof filteredData.location === 'string')
      return [filteredData.location];
    else if (Array.isArray(filteredData.location))
      return filteredData.location;

    return [];
  }
  return [];
});

function onFilterAccountsChanged(acc: BlockchainAccount<AddressData>[]): void {
  set(userAction, true);
  set(accounts, acc.length > 0 ? [acc[0]] : []);
}

function redecodeAllEvents(): void {
  set(decodingStatusDialogPersistent, true);
  show({
    message: t('transactions.events_decoding.confirmation'),
    title: t('transactions.events_decoding.redecode_all'),
  }, () => redecodeAllEventsHandler(), () => {
    set(decodingStatusDialogPersistent, false);
  });
}

async function redecodeAllEventsHandler(): Promise<void> {
  set(decodingStatusDialogPersistent, false);
  set(currentAction, 'decode');
  await fetchUndecodedTransactionsStatus();
  await redecodeTransactions(get(onlyChains));
  await fetchData();
}

async function forceRedecodeEvmEvents(data: PullEvmTransactionPayload): Promise<void> {
  set(currentAction, 'decode');
  await pullAndRedecodeTransactions(data);
  await fetchData();
}

function showForm(payload: ShowEventHistoryForm): void {
  if (payload.type === 'event') {
    set(formData, payload.data);
  }
  else {
    const { event, group } = payload.data;
    set(eventWithMissingRules, event);
    set(selectedGroupHeader, group);
  }
}

const { isActive, pause, resume } = useIntervalFn(() => {
  startPromise(fetchDataAndLocations());
}, 20000);

function onAddMissingRule(data: Pick<AccountingRuleEntry, 'eventType' | 'eventSubtype' | 'counterparty'>): void {
  router.push({
    path: '/settings/accounting',
    query: { 'add-rule': 'true', ...data },
  });
}

function editMissingRulesEntry(event: HistoryEventEntry): void {
  const group = get(selectedGroupHeader);

  startPromise(nextTick(() => {
    showForm({ data: { event, group }, type: 'event' });
  }));
}

async function refresh(userInitiated = false): Promise<void> {
  if (userInitiated)
    startPromise(historyEventMappings.refresh());
  else
    startPromise(fetchDataAndLocations());

  set(currentAction, 'query');
  const entryTypesVal = get(entryTypes) || [];
  const disableEvmEvents = entryTypesVal.length > 0 && !entryTypesVal.includes(HistoryEventEntryType.EVM_EVENT);
  await refreshTransactions(get(onlyChains), disableEvmEvents, userInitiated);
  startPromise(fetchDataAndLocations());
}

async function fetchAndRedecodeEvents(data?: PullEvmTransactionPayload): Promise<void> {
  await fetchDataAndLocations();
  if (data)
    await forceRedecodeEvmEvents(data);
}

function onShowDialog(type: 'decode' | 'protocol-refresh'): void {
  if (type === 'decode')
    set(decodingStatusDialogOpen, true);
  else
    set(protocolCacheStatusDialogOpen, true);
}

async function redecodePageTransactions(): Promise<void> {
  const evmEvents = get(groups).data.filter(isEvmEvent);
  const transactions = evmEvents.map(item => toEvmChainAndTxHash(item));

  await pullAndRedecodeTransactions({ transactions });
  await fetchUndecodedTransactionsStatus();
  await fetchData();
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

function addTxHash() {
  set(addTransactionModelValue, {
    associatedAddress: '',
    evmChain: '',
    txHash: '',
  });
}

function repullingTransactions() {
  set(repullingTransactionModelValue, {
    address: '',
    evmChain: '',
    fromTimestamp: 0,
    toTimestamp: 0,
  });
}

watchImmediate(route, async (route) => {
  if (route.query.openDecodingStatusDialog) {
    set(decodingStatusDialogOpen, true);
    await router.replace({ query: {} });
  }
});

watch(eventTaskLoading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchDataAndLocations();
});

watch(shouldFetchEventsRegularly, (shouldFetchEventsRegularly) => {
  const active = get(isActive);
  if (shouldFetchEventsRegularly && !active)
    resume();
  else if (!shouldFetchEventsRegularly && active)
    pause();
});

watch([filters, usedAccounts], ([filters, usedAccounts], [oldFilters, oldAccounts]) => {
  const filterChanged = !isEqual(filters, oldFilters);
  const accountsChanged = !isEqual(usedAccounts, oldAccounts);

  if (!(filterChanged || accountsChanged))
    return;

  if (accountsChanged && usedAccounts.length > 0) {
    const updatedFilter = { ...get(filters) };
    updateFilter(updatedFilter);
  }

  if (filterChanged || accountsChanged) {
    set(locationOverview, filters.location);
    setPage(1);
  }
});

onMounted(async () => {
  await refresh();
});

onUnmounted(() => {
  pause();
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
        :loading="eventTaskLoading"
        :include-evm-events="includes.evmEvents"
        @refresh="refresh(true)"
        @show:form="showForm($event)"
        @show:add-transaction-form="addTxHash()"
        @show:repulling-transactions-form="repullingTransactions()"
      />
    </template>

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
        :hide-account-selector="useExternalAccountFilter"
        @update:accounts="onFilterAccountsChanged($event)"
        @redecode="redecodeAllEvents()"
        @redecode-page="redecodePageTransactions()"
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
        :exclude-ignored="!toggles.showIgnoredAssets"
        :identifiers="identifiers"
        :highlighted-identifiers="highlightedIdentifiers"
        @show:form="showForm($event)"
        @refresh="fetchAndRedecodeEvents($event)"
        @set-page="setPage($event)"
      >
        <template #query-status="{ colspan }">
          <HistoryQueryStatus
            v-model:current-action="currentAction"
            :only-chains="onlyChains"
            :locations="locations"
            :decoding-status="decodingStatus"
            :decoding="eventTaskLoading"
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
        v-model="repullingTransactionModelValue"
        :loading="sectionLoading"
        @refresh="fetchAndRedecodeEvents()"
      />

      <MissingRulesDialog
        v-model="eventWithMissingRules"
        @edit-event="editMissingRulesEntry($event)"
        @redecode="forceRedecodeEvmEvents({ transactions: [$event] })"
        @add="onAddMissingRule($event)"
        @dismiss="eventWithMissingRules = undefined"
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
  </TablePageLayout>
</template>
