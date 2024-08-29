<script setup lang="ts">
import { isEqual } from 'lodash-es';
import { not } from '@vueuse/math';
import { type Account, type Blockchain, HistoryEventEntryType, type Writeable } from '@rotki/common';
import { IgnoreActionType } from '@/types/history/ignored';
import { RouterAccountsSchema } from '@/types/route';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import HistoryEventsAction from '@/components/history/events/HistoryEventsAction.vue';
import type {
  EvmChainAndTxHash,
  EvmHistoryEvent,
  HistoryEvent,
  HistoryEventEntry,
  HistoryEventRequestPayload,
} from '@/types/history/events';
import type { DataTableColumn } from '@rotki/ui-library';
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
const selectedGroupEventHeader = ref<HistoryEvent>();
const eventToDelete = ref<HistoryEventEntry>();
const eventWithMissingRules = ref<HistoryEventEntry>();
const missingRulesDialog = ref<boolean>(false);
const transactionToIgnore = ref<HistoryEventEntry>();
const accounts = ref<BlockchainAccount<AddressData>[]>([]);
const locationOverview = ref(get(location));
const toggles = ref<{ customizedEventsOnly: boolean; showIgnoredAssets: boolean }>({
  customizedEventsOnly: false,
  showIgnoredAssets: false,
});
const isEventsLoading = ref<boolean>(false);
const decodingStatusDialogPersistent = ref<boolean>(false);
const decodingStatusDialogOpen = ref<boolean>(false);
const protocolCacheStatusDialogOpen = ref<boolean>(false);
const currentAction = ref<'decode' | 'query'>('query');

const { isTaskRunning } = useTaskStore();
const { show } = useConfirmStore();
const { fetchAssociatedLocations, resetUndecodedTransactionsStatus } = useHistoryStore();
const { decodingStatus } = storeToRefs(useHistoryStore());
const { getAccountByAddress } = useBlockchainStore();
const { notify } = useNotificationsStore();
const { isAllFinished: isQueryingTxsFinished } = toRefs(useTxQueryStatusStore());
const { isAllFinished: isQueryingOnlineEventsFinished } = toRefs(useEventsQueryStatusStore());
const { isLoading: isSectionLoading } = useStatusStore();

const { fetchHistoryEvents, deleteHistoryEvent } = useHistoryEvents();
const { deleteTransactions } = useHistoryEventsApi();
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

const cols = computed<DataTableColumn<HistoryEventEntry>[]>(() => [
  {
    label: '',
    key: 'ignoredInAccounting',
    class: '!p-0 w-px',
    cellClass: '!p-0 w-px',
  },
  {
    label: t('transactions.events.headers.event_identifier'),
    key: 'txHash',
    class: 'w-[60%]',
    cellClass: '!py-2',
  },
  {
    label: t('common.datetime'),
    key: 'timestamp',
    cellClass: 'text-no-wrap !py-2',
    align: 'end',
    sortable: true,
  },
  {
    label: '',
    key: 'action',
    class: 'w-[1.25rem]',
    cellClass: 'w-[1.25rem] !py-2',
    align: 'end',
  },
  {
    label: '',
    key: 'expand',
    align: 'end',
    class: '!w-0 !p-0',
    cellClass: '!w-0 !p-0',
  },
]);

const includeEvmEvents: ComputedRef<boolean> = useEmptyOrSome(entryTypes, type => isEvmEventType(type));
const includeOnlineEvents: ComputedRef<boolean> = useEmptyOrSome(entryTypes, type => isOnlineHistoryEventType(type));

const {
  selected,
  isLoading: isEventsGroupHeaderLoading,
  userAction,
  state: eventsHeader,
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

const loading = refDebounced(logicOr(isEventsGroupHeaderLoading, isEventsLoading), 300);
const { data } = getCollectionData<HistoryEventEntry>(eventsHeader);

const { ignore, toggle } = useIgnore<HistoryEventEntry>({
  actionType: IgnoreActionType.HISTORY_EVENTS,
  toData: (item: HistoryEventEntry) => item.eventIdentifier,
}, selected, fetchData);

async function fetchDataAndLocations(): Promise<void> {
  await fetchData();
  await fetchAssociatedLocations();
}

const allEvents: Ref<HistoryEventEntry[]> = asyncComputed(async () => {
  const eventsHeaderData = get(data);

  if (eventsHeaderData.length === 0)
    return [];

  const response = await fetchHistoryEvents({
    limit: -1,
    offset: 0,
    eventIdentifiers: eventsHeaderData.map(item => item.eventIdentifier),
    groupByEventIds: false,
    excludeIgnoredAssets: !get(toggles, 'showIgnoredAssets'),
  });

  return response.data;
}, [], {
  lazy: true,
  evaluating: isEventsLoading,
});

const hasIgnoredEvent = computed<boolean>(() => get(allEvents).some(event => event.ignoredInAccounting));

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

async function resetEventsHandler(data: EvmHistoryEvent): Promise<void> {
  const eventIds = get(allEvents)
    .filter(event => isEvmEvent(event) && event.txHash === data.txHash && event.customized)
    .map(event => event.identifier);

  if (eventIds.length > 0)
    await deleteHistoryEvent(eventIds, true);

  await forceRedecodeEvmEvents(toEvmChainAndTxHash(data));
  await fetchDataAndLocations();
}

function resetEvents(data: EvmHistoryEvent): void {
  show({
    title: t('transactions.events.confirmation.reset.title'),
    message: t('transactions.events.confirmation.reset.message'),
  }, () => resetEventsHandler(data));
}

function deleteTxAndEvents({ evmChain, txHash }: EvmChainAndTxHash): void {
  show({
    title: t('transactions.dialog.delete.title'),
    message: t('transactions.dialog.delete.message'),
  }, async () => {
    try {
      await deleteTransactions(evmChain, txHash);
      await fetchData();
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const title = t('transactions.dialog.delete.error.title');
        const message = t('transactions.dialog.delete.error.message', {
          message: error.message,
        });
        notify({
          title,
          message,
          display: true,
        });
      }
    }
  });
}

const { setOpenDialog, setPostSubmitFunc } = useHistoryEventsForm();

setPostSubmitFunc(() => {
  const groupHeader = get(selectedGroupEventHeader);
  if (groupHeader)
    fetchDataAndRefreshEvents(toEvmChainAndTxHash(groupHeader));
  else fetchDataAndLocations();
});

function suggestNextSequence(): string {
  const eventHeader = get(selectedGroupEventHeader);

  if (!eventHeader)
    return '0';

  const all = get(allEvents);

  if (!all?.length)
    return (Number(eventHeader.sequenceIndex) + 1).toString();

  const eventIdentifierHeader = eventHeader.eventIdentifier;
  const filtered = all
    .filter(({ eventIdentifier, hidden }) => eventIdentifier === eventIdentifierHeader && !hidden)
    .map(({ sequenceIndex }) => Number(sequenceIndex))
    .sort((a, b) => b - a);

  return ((filtered[0] ?? Number(eventHeader.sequenceIndex)) + 1).toString();
}

function addEvent(groupHeader?: HistoryEvent): void {
  set(selectedGroupEventHeader, groupHeader);
  set(editableItem, undefined);
  set(nextSequence, suggestNextSequence());
  setOpenDialog(true);
}

function editEventHandler(event: HistoryEvent, groupHeader?: HistoryEvent): void {
  set(selectedGroupEventHeader, groupHeader);
  set(editableItem, event);
  set(nextSequence, undefined);
  setOpenDialog(true);
}

function promptForDelete({ item, canDelete }: { item: HistoryEventEntry; canDelete: boolean }): void {
  if (canDelete)
    set(eventToDelete, item);
  else
    set(transactionToIgnore, item);

  showDeleteConfirmation();
}

async function deleteEventHandler(): Promise<void> {
  const txToIgnore = get(transactionToIgnore);
  if (txToIgnore) {
    set(selected, [txToIgnore]);
    await ignore(true);
  }

  const eventToDeleteVal = get(eventToDelete);
  const id = eventToDeleteVal?.identifier;

  if (eventToDeleteVal && id) {
    const { success } = await deleteHistoryEvent([id]);
    if (!success)
      return;

    await fetchDataAndRefreshEvents(toEvmChainAndTxHash(eventToDeleteVal));
  }

  set(eventToDelete, null);
  set(transactionToIgnore, null);
}

function getItemClass(item: HistoryEventEntry): '' | 'opacity-50' {
  return item.ignoredInAccounting ? 'opacity-50' : '';
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

function resetPendingDeletion(): void {
  set(eventToDelete, null);
  set(transactionToIgnore, null);
}

function setMissingRulesDialog(event: HistoryEventEntry, groupHeader: HistoryEvent): void {
  set(eventWithMissingRules, event);
  set(selectedGroupEventHeader, groupHeader);
  set(missingRulesDialog, true);
}

function editMissingRulesEntry(event?: HistoryEventEntry): void {
  if (!event)
    return;

  const groupHeader = get(selectedGroupEventHeader);
  set(missingRulesDialog, false);
  editEventHandler(event, groupHeader);
}

function showDeleteConfirmation(): void {
  const text = get(transactionToIgnore)
    ? {
        title: t('transactions.events.confirmation.ignore.title'),
        message: t('transactions.events.confirmation.ignore.message'),
        primaryAction: t('transactions.events.confirmation.ignore.action'),
      }
    : {
        title: t('transactions.events.confirmation.delete.title'),
        message: t('transactions.events.confirmation.delete.message'),
        primaryAction: t('common.actions.confirm'),
      };
  show(text, deleteEventHandler, resetPendingDeletion);
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

const { setOpenDialog: setTxFormOpenDialog, setPostSubmitFunc: setTxFormPostSubmitFunc } = useHistoryTransactionsForm();

setTxFormPostSubmitFunc((payload) => {
  if (payload)
    fetchDataAndRefreshEvents(payload, true);
});

function addTransactionHash(): void {
  setTxFormOpenDialog(true);
}

async function fetchDataAndRefreshEvents(data: EvmChainAndTxHash, reDecodeEvents = false): Promise<void> {
  await fetchDataAndLocations();
  if (reDecodeEvents)
    await forceRedecodeEvmEvents(data);
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
      <RuiTooltip :open-delay="400">
        <template #activator>
          <RuiButton
            :disabled="processing"
            variant="outlined"
            color="primary"
            @click="refresh(true)"
          >
            <template #prepend>
              <RuiIcon name="refresh-line" />
            </template>
            {{ t('common.refresh') }}
          </RuiButton>
        </template>
        {{ t('transactions.refresh_tooltip') }}
      </RuiTooltip>
      <RuiButton
        color="primary"
        data-cy="history-events__add"
        @click="addEvent()"
      >
        <template #prepend>
          <RuiIcon name="add-line" />
        </template>
        {{ t('transactions.actions.add_event') }}
      </RuiButton>

      <RuiMenu
        :popper="{ placement: 'bottom-end' }"
        menu-class="max-w-[24rem]"
        close-on-content-click
      >
        <template #activator="{ attrs }">
          <RuiBadge
            :model-value="eventTaskLoading"
            color="primary"
            dot
            placement="top"
            offset-y="12"
            offset-x="-12"
          >
            <RuiButton
              variant="text"
              icon
              size="sm"
              class="!p-2"
              v-bind="attrs"
            >
              <RuiIcon name="more-2-fill" />
            </RuiButton>
          </RuiBadge>
        </template>
        <div class="py-2">
          <template v-if="includeEvmEvents">
            <RuiButton
              variant="list"
              @click="decodingStatusDialogOpen = true"
            >
              <template #prepend>
                <RuiBadge
                  :model-value="eventTaskLoading"
                  color="primary"
                  dot
                  placement="top"
                  offset-y="4"
                  offset-x="-4"
                >
                  <RuiIcon name="file-info-line" />
                </RuiBadge>
              </template>
              {{ t('transactions.events_decoding.title') }}
            </RuiButton>
          </template>

          <RuiButton
            variant="list"
            data-cy="history-events__add_by_tx_hash"
            :disabled="eventTaskLoading"
            @click="addTransactionHash()"
          >
            <template #prepend>
              <RuiIcon name="add-line" />
            </template>
            {{ t('transactions.dialog.add_tx') }}
          </RuiButton>
        </div>
      </RuiMenu>
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
      />

      <CollectionHandler
        :collection="eventsHeader"
        @set-page="setPage($event)"
      >
        <template #default="{ data: eventsData, showUpgradeRow, limit, total, found, entriesFoundTotal }">
          <RuiDataTable
            v-model:pagination.external="pagination"
            v-model:sort.external="sort"
            :expanded="eventsData"
            :cols="cols"
            :rows="eventsData"
            :loading="loading"
            :item-class="getItemClass"
            :empty="{ label: t('data_table.no_data') }"
            :texts="{
              rowsPerPage: t('data_table.rows_per_page'),
              itemsNumber: t('data_table.items_no'),
              of: t('common.of'),
            }"
            row-attr="identifier"
            outlined
          >
            <template #item.ignoredInAccounting="{ row }">
              <IgnoredInAcountingIcon
                v-if="row.ignoredInAccounting"
                class="ml-4"
              />
              <div
                v-else
                class="min-h-[3.25rem]"
              />
            </template>
            <template #item.txHash="{ row }">
              <LazyLoader class="flex items-center gap-2">
                <LocationIcon
                  icon
                  :item="row.location"
                  size="20px"
                />
                <HistoryEventsIdentifier :event="row" />
              </LazyLoader>
            </template>
            <template #item.timestamp="{ row }">
              <LazyLoader>
                <DateDisplay
                  :timestamp="row.timestamp"
                  milliseconds
                />
              </LazyLoader>
            </template>
            <template #item.action="{ row }">
              <LazyLoader>
                <HistoryEventsAction
                  :event="row"
                  :loading="eventTaskLoading"
                  @add-event="addEvent($event)"
                  @toggle-ignore="toggle($event)"
                  @redecode="forceRedecodeEvmEvents($event)"
                  @reset="resetEvents($event)"
                  @delete-tx="deleteTxAndEvents($event)"
                />
              </LazyLoader>
            </template>
            <template #item.expand />
            <template #expanded-item="{ row }">
              <HistoryEventsList
                class="-my-4"
                :class="{ 'opacity-50': row.ignoredInAccounting }"
                :all-events="allEvents"
                :event-group="row"
                :loading="sectionLoading || eventTaskLoading"
                :has-ignored-event="hasIgnoredEvent"
                @edit-event="editEventHandler($event, row)"
                @delete-event="promptForDelete($event)"
                @show:missing-rule-action="setMissingRulesDialog($event, row)"
              />
            </template>
            <template #body.prepend="{ colspan }">
              <HistoryQueryStatus
                v-model:current-action="currentAction"
                :include-evm-events="includeEvmEvents"
                :include-online-events="includeOnlineEvents"
                :only-chains="onlyChains"
                :locations="locations"
                :decoding-status="decodingStatus"
                :decoding="eventTaskLoading"
                :colspan="colspan"
                :loading="processing"
                @show-decode-details="decodingStatusDialogOpen = true"
                @show-protocol-refresh-details="protocolCacheStatusDialogOpen = true"
              />
              <UpgradeRow
                v-if="showUpgradeRow"
                :limit="limit"
                :total="total"
                :found="found"
                :entries-found-total="entriesFoundTotal"
                :colspan="colspan"
                :label="t('common.events')"
              />
            </template>
          </RuiDataTable>
        </template>
      </CollectionHandler>

      <HistoryEventFormDialog
        :editable-item="editableItem"
        :group-header="selectedGroupEventHeader"
        :next-sequence="nextSequence"
      />

      <TransactionFormDialog :loading="sectionLoading" />

      <MissingRulesDialog
        v-if="missingRulesDialog"
        v-model="missingRulesDialog"
        :event="eventWithMissingRules"
        @edit="editMissingRulesEntry($event)"
        @re-decode="forceRedecodeEvmEvents($event)"
        @add-rule="onAddMissingRule($event)"
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
