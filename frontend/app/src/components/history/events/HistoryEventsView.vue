<script setup lang="ts">
import { isEqual } from 'lodash-es';
import { not } from '@vueuse/math';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { SavedFilterLocation } from '@/types/filtering';
import { IgnoreActionType } from '@/types/history/ignored';
import { RouterAccountsSchema } from '@/types/route';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import HistoryEventsAction from '@/components/history/events/HistoryEventsAction.vue';
import { Routes } from '@/router/routes';
import type {
  EvmChainAndTxHash,
  EvmHistoryEvent,
  HistoryEvent,
  HistoryEventEntry,
  HistoryEventRequestPayload,
} from '@/types/history/events';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library-compat';
import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { Writeable } from '@/types';
import type { Collection } from '@/types/collection';
import type { AccountingRuleEntry } from '@/types/settings/accounting';
import type { Blockchain } from '@rotki/common/lib/blockchain';
import type { Account } from '@rotki/common/lib/account';
import type { Filters, Matcher } from '@/composables/filters/events';

const props = withDefaults(
  defineProps<{
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
  }>(),
  {
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
  },
);

const { t } = useI18n();

const customizedEventsOnly: Ref<boolean> = ref(false);
const showIgnoredAssets: Ref<boolean> = ref(false);

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
const missingRulesDialog: Ref<boolean> = ref(false);
const transactionToIgnore = ref<HistoryEventEntry>();
const accounts = ref<BlockchainAccount<AddressData>[]>([]);
const locationOverview = ref(get(location));

const usedTitle: ComputedRef<string> = computed(
  () => get(sectionTitle) || t('transactions.title'),
);

const usedAccounts = computed<Account[]>(() => {
  if (isDefined(useExternalAccountFilter))
    return get(externalAccountFilter);

  const accountData = get(accounts).map(account => ({
    address: getAccountAddress(account),
    chain: account.chain,
  }));
  return accountData.length > 0 ? [accountData[0]] : accountData;
});

const sort: Ref<DataTableSortData> = ref({
  column: 'timestamp',
  direction: 'desc' as const,
});

const tableHeaders = computed<DataTableColumn[]>(() => [
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

const { isTaskRunning } = useTaskStore();
const { show } = useConfirmStore();
const historyStore = useHistoryStore();
const { fetchAssociatedLocations, resetUndecodedTransactionsStatus } = historyStore;
const { decodingStatus } = storeToRefs(historyStore);
const { txChains } = useSupportedChains();
const txChainIds = useArrayMap(txChains, x => x.id);

const { fetchHistoryEvents, deleteHistoryEvent } = useHistoryEvents();
const { deleteTransactions } = useHistoryEventsApi();

const { refreshTransactions } = useHistoryTransactions();

const {
  pullAndRedecodeTransaction,
  fetchUndecodedTransactionsStatus,
  redecodeTransactions,
} = useHistoryTransactionDecoding();
const { getAccountByAddress } = useBlockchainStore();

const { notify } = useNotificationsStore();

const vueRouter = useRouter();

const {
  options,
  selected,
  isLoading: isEventsGroupHeaderLoading,
  userAction,
  state: eventsHeader,
  filters,
  matchers,
  setPage,
  setTableOptions,
  setFilter,
  updateFilter,
  fetchData,
  pageParams,
  editableItem,
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
  () =>
    useHistoryEventFilter(
      {
        protocols: get(protocols).length > 0,
        locations: !!get(location),
        period: !!get(period),
        validators: !!get(validators),
        eventTypes: get(eventTypes).length > 0,
        eventSubtypes: get(eventSubTypes).length > 0,
      },
      entryTypes,
    ),
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
      accounts: get(usedAccounts).map(
        account => `${account.address}#${account.chain}`,
      ),
      customizedEventsOnly: get(customizedEventsOnly),
      excludeIgnoredAssets: !get(showIgnoredAssets),
    })),
    defaultParams: computed<Partial<HistoryEventRequestPayload> | undefined>(
      () => {
        if (isDefined(entryTypes)) {
          return {
            entryTypes: {
              values: get(entryTypes),
            },
          };
        }
        return undefined;
      },
    ),
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

async function fetchDataAndLocations() {
  await fetchData();
  await fetchAssociatedLocations();
}

const { data } = getCollectionData<HistoryEventEntry>(eventsHeader);

const isEventsLoading: Ref<boolean> = ref(false);
const decodingStatusDialogPersistent: Ref<boolean> = ref(false);
const decodingStatusDialogOpen: Ref<boolean> = ref(false);
const currentAction: Ref<'decode' | 'query'> = ref('query');
const route = useRoute();

const allEvents: Ref<HistoryEventEntry[]> = asyncComputed(
  async () => {
    const eventsHeaderData = get(data);

    if (eventsHeaderData.length === 0)
      return [];

    const response = await fetchHistoryEvents({
      limit: -1,
      offset: 0,
      eventIdentifiers: eventsHeaderData.map(item => item.eventIdentifier),
      groupByEventIds: false,
      excludeIgnoredAssets: !get(showIgnoredAssets),
    });

    return response.data;
  },
  [],
  {
    lazy: true,
    evaluating: isEventsLoading,
  },
);

const hasIgnoredEvent = computed(() => get(allEvents).some(event => event.ignoredInAccounting));

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

function onFilterAccountsChanged(acc: BlockchainAccount<AddressData>[]) {
  set(userAction, true);
  set(accounts, acc.length > 0 ? [acc[0]] : []);
}

function redecodeAllEvents() {
  set(decodingStatusDialogPersistent, true);
  show(
    {
      title: t('transactions.events_decoding.redecode_all'),
      message: t('transactions.events_decoding.confirmation'),
    },
    () => redecodeAllEventsHandler(),
    () => {
      set(decodingStatusDialogPersistent, false);
    },
  );
}

async function redecodeAllEventsHandler() {
  set(decodingStatusDialogPersistent, false);
  set(currentAction, 'decode');
  await fetchUndecodedTransactionsStatus();
  await redecodeTransactions(get(onlyChains));
  await fetchData();
}

async function forceRedecodeEvmEvents(data: EvmChainAndTxHash) {
  set(currentAction, 'decode');
  await pullAndRedecodeTransaction(data);
  await fetchData();
}

async function resetEventsHandler(data: EvmHistoryEvent) {
  const eventIds = get(allEvents)
    .filter(
      event =>
        isEvmEvent(event) && event.txHash === data.txHash && event.customized,
    )
    .map(event => event.identifier);

  if (eventIds.length > 0)
    await deleteHistoryEvent(eventIds, true);

  await forceRedecodeEvmEvents(toEvmChainAndTxHash(data));
  await fetchDataAndLocations();
}

function resetEvents(data: EvmHistoryEvent) {
  show(
    {
      title: t('transactions.events.confirmation.reset.title'),
      message: t('transactions.events.confirmation.reset.message'),
    },
    () => resetEventsHandler(data),
  );
}

function deleteTxAndEvents({ evmChain, txHash }: EvmChainAndTxHash) {
  show(
    {
      title: t('transactions.dialog.delete.title'),
      message: t('transactions.dialog.delete.message'),
    },
    async () => {
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
    },
  );
}

const { ignore } = useIgnore<HistoryEventEntry>(
  {
    actionType: IgnoreActionType.HISTORY_EVENTS,
    toData: (item: HistoryEventEntry) => item.eventIdentifier,
  },
  selected,
  fetchData,
);

async function toggleIgnore(item: HistoryEventEntry) {
  set(selected, [item]);
  await ignore(!item.ignoredInAccounting);
}

const { setOpenDialog, setPostSubmitFunc } = useHistoryEventsForm();

setPostSubmitFunc(() => {
  const groupHeader = get(selectedGroupEventHeader);
  if (groupHeader)
    fetchDataAndRefreshEvents(toEvmChainAndTxHash(groupHeader));
  else
    fetchDataAndLocations();
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
    .filter(
      ({ eventIdentifier, hidden }) =>
        eventIdentifier === eventIdentifierHeader && !hidden,
    )
    .map(({ sequenceIndex }) => Number(sequenceIndex))
    .sort((a, b) => b - a);

  return ((filtered[0] ?? Number(eventHeader.sequenceIndex)) + 1).toString();
}

function addEvent(groupHeader?: HistoryEvent) {
  set(selectedGroupEventHeader, groupHeader);
  set(editableItem, undefined);
  set(nextSequence, suggestNextSequence());
  setOpenDialog(true);
}

function editEventHandler(event: HistoryEvent, groupHeader?: HistoryEvent) {
  set(selectedGroupEventHeader, groupHeader);
  set(editableItem, event);
  set(nextSequence, undefined);
  setOpenDialog(true);
}

function promptForDelete({
  item,
  canDelete,
}: {
  item: HistoryEventEntry;
  canDelete: boolean;
}) {
  if (canDelete)
    set(eventToDelete, item);
  else
    set(transactionToIgnore, item);

  showDeleteConfirmation();
}

async function deleteEventHandler() {
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

function getItemClass(item: HistoryEventEntry) {
  return item.ignoredInAccounting ? 'opacity-50' : '';
}

watch(
  [filters, usedAccounts],
  ([filters, usedAccounts], [oldFilters, oldAccounts]) => {
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
      set(options, { ...get(options), page: 1 });
    }
  },
);

const premium = usePremium();
const { isLoading: isSectionLoading } = useStatusStore();
const sectionLoading = isSectionLoading(Section.HISTORY_EVENT);
const eventTaskLoading = isTaskRunning(TaskType.TRANSACTIONS_DECODING);
const onlineHistoryEventsLoading = isTaskRunning(TaskType.QUERY_ONLINE_EVENTS);
const isTransactionsLoading = isTaskRunning(TaskType.TX);

const { isAllFinished: isQueryingTxsFinished } = toRefs(
  useTxQueryStatusStore(),
);
const { isAllFinished: isQueryingOnlineEventsFinished } = toRefs(
  useEventsQueryStatusStore(),
);

const refreshing = logicOr(
  sectionLoading,
  eventTaskLoading,
  onlineHistoryEventsLoading,
);

const querying = not(
  logicOr(isQueryingTxsFinished, isQueryingOnlineEventsFinished),
);

const shouldFetchEventsRegularly = logicOr(querying, refreshing);

const loading = refThrottled(
  logicOr(isEventsGroupHeaderLoading, isEventsLoading),
  300,
);

const processing = logicOr(
  isTransactionsLoading,
  loading,
  querying,
  refreshing,
);

const { pause, resume, isActive } = useIntervalFn(() => {
  startPromise(fetchDataAndLocations());
}, 20000);

watch(shouldFetchEventsRegularly, (shouldFetchEventsRegularly) => {
  const active = get(isActive);
  if (shouldFetchEventsRegularly && !active)
    resume();
  else if (!shouldFetchEventsRegularly && active)
    pause();
});

function onAddMissingRule(data: Pick<AccountingRuleEntry, 'eventType' | 'eventSubtype' | 'counterparty'>) {
  vueRouter.push({
    path: Routes.SETTINGS_ACCOUNTING,
    query: { 'add-rule': 'true', ...data },
  });
}

function resetPendingDeletion() {
  set(eventToDelete, null);
  set(transactionToIgnore, null);
}

function setMissingRulesDialog(event: HistoryEventEntry, groupHeader: HistoryEvent) {
  set(eventWithMissingRules, event);
  set(selectedGroupEventHeader, groupHeader);
  set(missingRulesDialog, true);
}

function editMissingRulesEntry(event?: HistoryEventEntry) {
  if (!event)
    return;

  const groupHeader = get(selectedGroupEventHeader);
  set(missingRulesDialog, false);
  editEventHandler(event, groupHeader);
}

function showDeleteConfirmation() {
  show(
    get(transactionToIgnore)
      ? {
          title: t('transactions.events.confirmation.ignore.title'),
          message: t('transactions.events.confirmation.ignore.message'),
          primaryAction: t('transactions.events.confirmation.ignore.action'),
        }
      : {
          title: t('transactions.events.confirmation.delete.title'),
          message: t('transactions.events.confirmation.delete.message'),
          primaryAction: t('common.actions.confirm'),
        },
    deleteEventHandler,
    resetPendingDeletion,
  );
}

onMounted(async () => {
  await refresh();
});

async function refresh(userInitiated = false) {
  set(currentAction, 'query');
  const entryTypesVal = get(entryTypes) || [];
  const disableEvmEvents = entryTypesVal.length > 0 && !entryTypesVal.includes(HistoryEventEntryType.EVM_EVENT);
  await refreshTransactions(get(onlyChains), disableEvmEvents, userInitiated);
  startPromise(fetchDataAndLocations());
}

onUnmounted(() => {
  pause();
});

watch(eventTaskLoading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading)
    await fetchDataAndLocations();
});

const {
  setOpenDialog: setTxFormOpenDialog,
  setPostSubmitFunc: setTxFormPostSubmitFunc,
} = useHistoryTransactionsForm();

setTxFormPostSubmitFunc((payload) => {
  if (payload)
    fetchDataAndRefreshEvents(payload, true);
});

function addTransactionHash() {
  setTxFormOpenDialog(true);
}

async function fetchDataAndRefreshEvents(data: EvmChainAndTxHash, reDecodeEvents = false) {
  await fetchDataAndLocations();
  if (reDecodeEvents)
    await forceRedecodeEvmEvents(data);
}

const includeEvmEvents: ComputedRef<boolean> = useEmptyOrSome(
  entryTypes,
  type => isEvmEventType(type),
);

const includeOnlineEvents: ComputedRef<boolean> = useEmptyOrSome(
  entryTypes,
  type => isOnlineHistoryEventType(type),
);

watchImmediate(route, async (route) => {
  if (route.query.openDecodingStatusDialog) {
    set(decodingStatusDialogOpen, true);
    await vueRouter.replace({ query: {} });
  }
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
        <template #activator="{ on }">
          <RuiBadge
            :value="eventTaskLoading"
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
              v-on="on"
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
                  :value="eventTaskLoading"
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

      <HistoryTableActions hide-divider>
        <template #filter>
          <TableStatusFilter>
            <div class="py-1 max-w-[16rem]">
              <RuiSwitch
                v-model="customizedEventsOnly"
                color="primary"
                class="p-4"
                hide-details
                :label="t('transactions.filter.customized_only')"
              />
              <RuiDivider />
              <RuiSwitch
                v-model="showIgnoredAssets"
                color="primary"
                class="p-4"
                hide-details
                :label="t('transactions.filter.show_ignored_assets')"
              />
            </div>
          </TableStatusFilter>
          <TableFilter
            :matches="filters"
            :matchers="matchers"
            :location="SavedFilterLocation.HISTORY_EVENTS"
            :disabled="!premium"
            @update:matches="setFilter($event)"
          >
            <template #tooltip>
              <i18n
                tag="span"
                path="transactions.filtering_premium_hint"
              >
                <ExternalLink
                  class="!font-bold !text-white"
                  premium
                >
                  {{ t('common.website') }}
                </ExternalLink>
              </i18n>
            </template>
          </TableFilter>
        </template>

        <RuiButton
          color="primary"
          class="!py-2"
          :disabled="processing"
          @click="redecodeAllEvents()"
        >
          {{ t('transactions.events_decoding.redecode_all') }}
        </RuiButton>

        <HistoryEventsExport :filters="pageParams" />
        <BlockchainAccountSelector
          v-if="!useExternalAccountFilter"
          :value="accounts"
          :chains="txChainIds"
          dense
          :label="t('transactions.filter.account')"
          outlined
          no-padding
          multichain
          hide-chain-icon
          unique
          flat
          @input="onFilterAccountsChanged($event)"
        />
      </HistoryTableActions>

      <CollectionHandler
        :collection="eventsHeader"
        @set-page="setPage($event)"
      >
        <template
          #default="{
            data: eventsData,
            itemLength,
            showUpgradeRow,
            limit,
            total,
            found,
            entriesFoundTotal,
          }"
        >
          <RuiDataTable
            :expanded="eventsData"
            :cols="tableHeaders"
            :rows="eventsData"
            :loading="processing"
            :pagination="{
              limit: options.itemsPerPage,
              page: options.page,
              total: itemLength,
            }"
            :pagination-modifiers="{ external: true }"
            :sort.sync="sort"
            :sort-modifiers="{ external: true }"
            :item-class="getItemClass"
            :empty="{ label: t('data_table.no_data') }"
            :texts="{
              rowsPerPage: t('data_table.rows_per_page'),
              itemsNumber: t('data_table.items_no'),
              of: t('common.of'),
            }"
            row-attr="txHash"
            outlined
            @update:options="setTableOptions($event)"
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
                  @toggle-ignore="toggleIgnore($event)"
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
                :include-evm-events="includeEvmEvents"
                :include-online-events="includeOnlineEvents"
                :only-chains="onlyChains"
                :locations="locations"
                :decoding-status="decodingStatus"
                :decoding="eventTaskLoading"
                :colspan="colspan"
                :loading="processing"
                :current-action.sync="currentAction"
                @show-decode-details="decodingStatusDialogOpen = true"
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
  </TablePageLayout>
</template>
