<script setup lang="ts">
import { isEqual } from 'lodash-es';
import { not } from '@vueuse/math';
import { type Account, type Blockchain, HistoryEventEntryType, type Writeable } from '@rotki/common';
import { RouterAccountsSchema } from '@/types/route';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type {
  EvmChainAndTxHash,
  HistoryEvent,
  HistoryEventEntry,
  HistoryEventRequestPayload,
  ShowEventHistoryForm,
} from '@/types/history/events';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { Collection } from '@/types/collection';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import type { Filters, Matcher } from '@/composables/filters/events';

const props = withDefaults(defineProps<{
  location?: string;
  protocols?: string[];
  eventTypes?: string[];
  eventSubTypes?: string[];
  entryTypes?: HistoryEventEntryType[];
  period?: { fromTimestamp?: string; toTimestamp?: string };
  validators?: number[];
  externalAccountFilter?: Account[];
  useExternalAccountFilter?: boolean;
  sectionTitle?: string;
  mainPage?: boolean;
  onlyChains?: Blockchain[];
}>(), {
  location: undefined,
  protocols: () => [],
  eventTypes: () => [],
  eventSubTypes: () => [],
  entryTypes: undefined,
  period: undefined,
  validators: undefined,
  externalAccountFilter: () => [],
  useExternalAccountFilter: undefined,
  sectionTitle: '',
  mainPage: false,
  onlyChains: () => [],
});

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

const {
  location,
  protocols,
  entryTypes,
  period,
  validators,
  useExternalAccountFilter,
  externalAccountFilter,
  sectionTitle,
  eventTypes,
  eventSubTypes,
  mainPage,
  onlyChains,
} = toRefs(props);

const nextSequence = ref<string>();
const selectedGroup = ref<HistoryEvent>();
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

const { isTaskRunning } = useTaskStore();
const { show } = useConfirmStore();
const { fetchAssociatedLocations, resetUndecodedTransactionsStatus } = useHistoryStore();
const { decodingStatus } = storeToRefs(useHistoryStore());
const { getAccountByAddress } = useBlockchainStore();
const { isAllFinished: isQueryingTxsFinished } = toRefs(useTxQueryStatusStore());
const { isAllFinished: isQueryingOnlineEventsFinished } = toRefs(useEventsQueryStatusStore());
const { isLoading: isSectionLoading } = useStatusStore();

const { fetchHistoryEvents } = useHistoryEvents();

const { refreshTransactions } = useHistoryTransactions();
const { pullAndRedecodeTransaction, fetchUndecodedTransactionsStatus, redecodeTransactions } = useHistoryTransactionDecoding();
const historyEventMappings = useHistoryEventMappings();

const sectionLoading = isSectionLoading(Section.HISTORY_EVENT);
const eventTaskLoading = isTaskRunning(TaskType.TRANSACTIONS_DECODING);
const protocolCacheUpdatesLoading = isTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
const onlineHistoryEventsLoading = isTaskRunning(TaskType.QUERY_ONLINE_EVENTS);
const isTransactionsLoading = isTaskRunning(TaskType.TX);

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

const {
  isLoading: groupLoading,
  userAction,
  state: groups,
  filters,
  matchers,
  setPage,
  updateFilter,
  fetchData,
  pageParams,
  editableItem,
  pagination,
  sort,
} = usePaginationFilters<
  HistoryEvent,
  HistoryEventRequestPayload,
  HistoryEventEntry,
  Collection<HistoryEventEntry>,
  Filters,
  Matcher
>(
  null,
  mainPage,
  () => useHistoryEventFilter({
    protocols: get(protocols).length > 0,
    locations: !!get(location),
    period: !!get(period),
    validators: !!get(validators),
    eventTypes: get(eventTypes).length > 0,
    eventSubtypes: get(eventSubTypes).length > 0,
  }, entryTypes),
  fetchHistoryEvents,
  {
    onUpdateFilters(query) {
      const parsedAccounts = RouterAccountsSchema.parse(query);
      const accountsParsed = parsedAccounts.accounts;
      if (!accountsParsed || accountsParsed.length === 0)
        set(accounts, []);
      else
        set(accounts, accountsParsed.map(({ address, chain }) => getAccountByAddress(address, chain)));
    },
    extraParams: computed(() => ({
      accounts: get(usedAccounts).map(account => `${account.address}#${account.chain}`),
      customizedEventsOnly: get(toggles, 'customizedEventsOnly'),
      excludeIgnoredAssets: !get(toggles, 'showIgnoredAssets'),
    })),
    defaultParams: computed<Partial<HistoryEventRequestPayload> | undefined>(() => {
      if (isDefined(entryTypes)) {
        return {
          entryTypes: {
            values: get(entryTypes),
          },
        };
      }
      return undefined;
    }),
    customPageParams: computed<Partial<HistoryEventRequestPayload>>(() => {
      const params: Writeable<Partial<HistoryEventRequestPayload>> = {
        counterparties: get(protocols),
        eventTypes: get(eventTypes),
        eventSubtypes: get(eventSubTypes),
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
  },
);

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
    title: t('transactions.events_decoding.redecode_all'),
    message: t('transactions.events_decoding.confirmation'),
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

async function forceRedecodeEvmEvents(data: EvmChainAndTxHash): Promise<void> {
  set(currentAction, 'decode');
  await pullAndRedecodeTransaction(data);
  await fetchData();
}

const { setOpenDialog, setPostSubmitFunc } = useHistoryEventsForm();

setPostSubmitFunc(() => {
  fetchAndRedecodeEvents();
});

function showForm(payload: ShowEventHistoryForm): void {
  if (payload.type === 'event') {
    const {
      group,
      nextSequenceId,
      event,
    } = payload.data;

    set(selectedGroup, group);
    set(editableItem, event);
    set(nextSequence, nextSequenceId);
    setOpenDialog(true);
  }
  else {
    const { event, group } = payload.data;
    set(eventWithMissingRules, event);
    set(selectedGroup, group);
  }
}

const { pause, resume, isActive } = useIntervalFn(() => {
  startPromise(fetchDataAndLocations());
}, 20000);

function onAddMissingRule(data: Pick<AccountingRuleEntry, 'eventType' | 'eventSubtype' | 'counterparty'>): void {
  router.push({
    path: '/settings/accounting',
    query: { 'add-rule': 'true', ...data },
  });
}

function editMissingRulesEntry(event: HistoryEventEntry): void {
  const group = get(selectedGroup);

  startPromise(nextTick(() => {
    showForm({ type: 'event', data: { event, group } });
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

async function fetchAndRedecodeEvents(data?: EvmChainAndTxHash): Promise<void> {
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
        @reload="fetchAndRedecodeEvents($event)"
        @show:form="showForm($event)"
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
      />

      <HistoryEventsTable
        v-model:sort="sort"
        v-model:pagination="pagination"
        :group-loading="groupLoading"
        :groups="groups"
        :exclude-ignored="!toggles.showIgnoredAssets"
        @show:form="showForm($event)"
        @refresh="fetchAndRedecodeEvents($event)"
        @set-page="setPage($event)"
      >
        <template #query-status="{ colspan, eventsLoading }">
          <HistoryQueryStatus
            v-model:current-action="currentAction"
            :only-chains="onlyChains"
            :locations="locations"
            :decoding-status="decodingStatus"
            :decoding="eventsLoading"
            :colspan="colspan"
            :loading="processing"
            @show:dialog="onShowDialog($event)"
          />
        </template>
      </HistoryEventsTable>

      <HistoryEventFormDialog
        :editable-item="editableItem"
        :group-header="selectedGroup"
        :next-sequence="nextSequence"
      />

      <TransactionFormDialog :loading="sectionLoading" />

      <MissingRulesDialog
        v-model="eventWithMissingRules"
        @edit-event="editMissingRulesEntry($event)"
        @redecode="forceRedecodeEvmEvents($event)"
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
          <RuiIcon name="close-line" />
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
          <RuiIcon name="close-line" />
        </RuiButton>
      </HistoryEventsProtocolCacheUpdateStatus>
    </RuiDialog>
  </TablePageLayout>
</template>
