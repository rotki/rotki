<script setup lang="ts">
import { type Account, type GeneralAccount } from '@rotki/common/lib/account';
import {
  type Blockchain,
  type BlockchainSelection
} from '@rotki/common/lib/blockchain';
import { isEqual } from 'lodash-es';
import { type ComputedRef, type Ref } from 'vue';
import { not } from '@vueuse/math';
import { HistoryEventEntryType } from '@rotki/common/lib/history/events';
import { type AccountingRuleEntry } from '@/types/settings/accounting';
import { type DataTableHeader } from '@/types/vuetify';
import { type Collection } from '@/types/collection';
import { SavedFilterLocation } from '@/types/filtering';
import { IgnoreActionType } from '@/types/history/ignored';
import {
  type EvmChainAndTxHash,
  type EvmHistoryEvent,
  type HistoryEvent,
  type HistoryEventEntry,
  type HistoryEventRequestPayload
} from '@/types/history/events';
import { RouterAccountsSchema } from '@/types/route';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { type Writeable } from '@/types';
import HistoryEventsAction from '@/components/history/events/HistoryEventsAction.vue';
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
    useExternalAccountFilter: false,
    sectionTitle: '',
    mainPage: false,
    onlyChains: () => []
  }
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
  onlyChains
} = toRefs(props);

const nextSequence = ref<string>();
const selectedGroupEventHeader = ref<HistoryEvent>();
const eventToDelete = ref<HistoryEventEntry>();
const eventWithMissingRules = ref<HistoryEventEntry>();
const missingRulesDialog: Ref<boolean> = ref(false);
const transactionToIgnore = ref<HistoryEventEntry>();
const accounts: Ref<GeneralAccount[]> = ref([]);
const locationOverview = ref(get(location));

const usedTitle: ComputedRef<string> = computed(
  () => get(sectionTitle) || t('transactions.title')
);

const usedAccounts: ComputedRef<Account<BlockchainSelection>[]> = computed(
  () => {
    if (get(useExternalAccountFilter)) {
      return get(externalAccountFilter);
    }
    const accountsVal = get(accounts);
    return accountsVal.length > 0 ? [accountsVal[0]] : accountsVal;
  }
);

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: '',
    value: 'ignoredInAccounting',
    sortable: false,
    class: 'pa-0',
    cellClass: 'pa-0',
    width: '0px'
  },
  {
    text: t('transactions.events.headers.event_identifier'),
    value: 'txHash',
    sortable: false,
    width: '60%'
  },
  {
    text: t('common.datetime'),
    value: 'timestamp',
    cellClass: 'text-no-wrap',
    align: 'end'
  },
  {
    text: '',
    value: 'action',
    width: '20px',
    align: 'end',
    sortable: false
  }
]);

const { isTaskRunning } = useTaskStore();
const { txEvmChains, getEvmChainName } = useSupportedChains();
const txChains = useArrayMap(txEvmChains, x => x.id);

const { fetchHistoryEvents, deleteHistoryEvent } = useHistoryEvents();

const { refreshTransactions } = useHistoryTransactions();

const { fetchTransactionEvents } = useHistoryTransactionDecoding();

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
  setOptions,
  setFilter,
  updateFilter,
  fetchData,
  pageParams,
  editableItem
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
        eventSubtypes: get(eventSubTypes).length > 0
      },
      entryTypes
    ),
  fetchHistoryEvents,
  {
    onUpdateFilters(query) {
      const parsedAccounts = RouterAccountsSchema.parse(query);
      const accountsParsed = parsedAccounts.accounts;
      if (!accountsParsed) {
        set(accounts, []);
      } else {
        set(accounts, accountsParsed.length > 0 ? [accountsParsed[0]] : []);
      }
    },
    extraParams: computed(() => ({
      accounts: get(usedAccounts).map(
        account => `${account.address}#${account.chain}`
      ),
      customizedEventsOnly: get(customizedEventsOnly),
      excludeIgnoredAssets: !get(showIgnoredAssets)
    })),
    defaultParams: computed<Partial<HistoryEventRequestPayload> | undefined>(
      () => {
        if (isDefined(entryTypes)) {
          return {
            entryTypes: {
              values: get(entryTypes)
            }
          };
        }
        return undefined;
      }
    ),
    customPageParams: computed<Partial<HistoryEventRequestPayload>>(() => {
      const params: Writeable<Partial<HistoryEventRequestPayload>> = {
        counterparties: get(protocols),
        eventTypes: get(eventTypes),
        eventSubtypes: get(eventSubTypes),
        groupByEventIds: true
      };

      const accounts = get(usedAccounts);

      if (isDefined(locationOverview)) {
        params.location = toSnakeCase(get(locationOverview));
      }

      if (accounts.length > 0) {
        params.locationLabels = accounts.map(({ address }) => address);
      }

      if (isDefined(period)) {
        const { fromTimestamp, toTimestamp } = get(period);
        params.fromTimestamp = fromTimestamp;
        params.toTimestamp = toTimestamp;
      }

      if (isDefined(validators)) {
        params.validatorIndices = get(validators).map(v => v.toString());
      }

      return params;
    })
  }
);

const { data } = getCollectionData<HistoryEventEntry>(eventsHeader);

const isEventsLoading: Ref<boolean> = ref(false);

const allEvents: Ref<HistoryEventEntry[]> = asyncComputed(
  async () => {
    const eventsHeaderData = get(data);

    if (eventsHeaderData.length === 0) {
      return [];
    }

    const response = await fetchHistoryEvents({
      limit: -1,
      offset: 0,
      eventIdentifiers: eventsHeaderData.map(item => item.eventIdentifier),
      groupByEventIds: false,
      excludeIgnoredAssets: !get(showIgnoredAssets)
    });

    return response.data;
  },
  [],
  {
    lazy: true,
    evaluating: isEventsLoading
  }
);

const locations = computed<string[]>(() => {
  const filteredData = get(filters);

  if ('location' in filteredData) {
    if (typeof filteredData.location === 'string') {
      return [filteredData.location];
    } else if (Array.isArray(filteredData.location)) {
      return filteredData.location;
    }
    return [];
  }
  return [];
});

const onFilterAccountsChanged = (acc: Account<BlockchainSelection>[]) => {
  set(userAction, true);
  set(accounts, acc.length > 0 ? [acc[0]] : []);
};

const redecodeAllEvmEvents = () => {
  set(decodingStatusDialogPersistent, true);
  show(
    {
      title: t('transactions.events_decoding.redecode_all'),
      message: t('transactions.events_decoding.confirmation')
    },
    () => redecodeAllEvmEventsHandler(),
    () => {
      set(decodingStatusDialogPersistent, false);
    }
  );
};

const redecodeAllEvmEventsHandler = async () => {
  set(decodingStatusDialogPersistent, false);

  const chains = get(onlyChains);
  const evmChains: { evmChain: string }[] = [];

  if (chains.length > 0) {
    chains.forEach(item => {
      const evmChain = getEvmChainName(item);
      if (evmChain) {
        evmChains.push({ evmChain });
      }
    });
  }

  await fetchTransactionEvents(chains.length === 0 ? null : evmChains, true);
};

const forceRedecodeEvmEvents = async (data: EvmChainAndTxHash) => {
  await fetchTransactionEvents([data], true);
};

const resetEventsHandler = async (data: EvmHistoryEvent) => {
  const eventIds = get(allEvents)
    .filter(
      event =>
        isEvmEvent(event) && event.txHash === data.txHash && event.customized
    )
    .map(event => event.identifier);

  if (eventIds.length > 0) {
    await deleteHistoryEvent(eventIds, true);
  }

  await forceRedecodeEvmEvents(toEvmChainAndTxHash(data));
  await fetchData();
};

const resetEvents = (data: EvmHistoryEvent) => {
  show(
    {
      title: t('transactions.events.confirmation.reset.title'),
      message: t('transactions.events.confirmation.reset.message')
    },
    () => resetEventsHandler(data)
  );
};

const { ignore } = useIgnore<HistoryEventEntry>(
  {
    actionType: IgnoreActionType.HISTORY_EVENTS,
    toData: (item: HistoryEventEntry) => item.eventIdentifier
  },
  selected,
  fetchData
);

const toggleIgnore = async (item: HistoryEventEntry) => {
  set(selected, [item]);
  await ignore(!item.ignoredInAccounting);
};

const { setOpenDialog, setPostSubmitFunc } = useHistoryEventsForm();

setPostSubmitFunc(() => {
  const groupHeader = get(selectedGroupEventHeader);
  if (groupHeader) {
    fetchDataAndRefreshEvents(toEvmChainAndTxHash(groupHeader));
  } else {
    fetchData();
  }
});

const suggestNextSequence = (): string => {
  const eventHeader = get(selectedGroupEventHeader);

  if (!eventHeader) {
    return '0';
  }

  const all = get(allEvents);

  if (!all?.length) {
    return (Number(eventHeader.sequenceIndex) + 1).toString();
  }

  const eventIdentifierHeader = eventHeader.eventIdentifier;
  const filtered = all
    .filter(
      ({ eventIdentifier, hidden }) =>
        eventIdentifier === eventIdentifierHeader && !hidden
    )
    .map(({ sequenceIndex }) => Number(sequenceIndex))
    .sort((a, b) => b - a);

  return ((filtered[0] ?? Number(eventHeader.sequenceIndex)) + 1).toString();
};

const addEvent = (groupHeader?: HistoryEvent) => {
  set(selectedGroupEventHeader, groupHeader);
  set(editableItem, undefined);
  set(nextSequence, suggestNextSequence());
  setOpenDialog(true);
};

const editEventHandler = (event: HistoryEvent, groupHeader?: HistoryEvent) => {
  set(selectedGroupEventHeader, groupHeader);
  set(editableItem, event);
  set(nextSequence, undefined);
  setOpenDialog(true);
};

const promptForDelete = ({
  item,
  canDelete
}: {
  item: HistoryEventEntry;
  canDelete: boolean;
}) => {
  if (canDelete) {
    set(eventToDelete, item);
  } else {
    set(transactionToIgnore, item);
  }
  showDeleteConfirmation();
};

const deleteEventHandler = async () => {
  const txToIgnore = get(transactionToIgnore);
  if (txToIgnore) {
    set(selected, [txToIgnore]);
    await ignore(true);
  }

  const eventToDeleteVal = get(eventToDelete);
  const id = eventToDeleteVal?.identifier;

  if (eventToDeleteVal && id) {
    const { success } = await deleteHistoryEvent([id]);
    if (!success) {
      return;
    }
    await fetchDataAndRefreshEvents(toEvmChainAndTxHash(eventToDeleteVal));
  }

  set(eventToDelete, null);
  set(transactionToIgnore, null);
};

const getItemClass = (item: HistoryEventEntry) =>
  item.ignoredInAccounting ? 'darken-row' : '';

watch(
  [filters, usedAccounts],
  async ([filters, usedAccounts], [oldFilters, oldAccounts]) => {
    const filterChanged = !isEqual(filters, oldFilters);
    const accountsChanged = !isEqual(usedAccounts, oldAccounts);

    if (!(filterChanged || accountsChanged)) {
      return;
    }

    if (accountsChanged && usedAccounts.length > 0) {
      const updatedFilter = { ...get(filters) };
      updateFilter(updatedFilter);
    }

    if (filterChanged || accountsChanged) {
      set(locationOverview, filters.location);
      set(options, { ...get(options), page: 1 });
    }
  }
);

const premium = usePremium();
const { isLoading: isSectionLoading } = useStatusStore();
const sectionLoading = isSectionLoading(Section.HISTORY_EVENT);
const eventTaskLoading = isTaskRunning(TaskType.EVM_EVENTS_DECODING);
const onlineHistoryEventsLoading = isTaskRunning(TaskType.QUERY_ONLINE_EVENTS);

const { isAllFinished: isQueryingTxsFinished } = toRefs(
  useTxQueryStatusStore()
);
const { isAllFinished: isQueryingOnlineEventsFinished } = toRefs(
  useEventsQueryStatusStore()
);

const refreshing = logicOr(
  sectionLoading,
  eventTaskLoading,
  onlineHistoryEventsLoading
);

const querying = not(
  logicOr(isQueryingTxsFinished, isQueryingOnlineEventsFinished)
);

const shouldFetchEventsRegularly = logicOr(querying, refreshing);

const loading = refThrottled(
  logicOr(isEventsGroupHeaderLoading, isEventsLoading),
  300
);

const { fetchAssociatedLocations } = useHistoryStore();
const { pause, resume, isActive } = useIntervalFn(() => {
  fetchData();
  fetchAssociatedLocations();
}, 20000);

watch(shouldFetchEventsRegularly, shouldFetchEventsRegularly => {
  const active = get(isActive);
  if (shouldFetchEventsRegularly && !active) {
    resume();
  } else if (!shouldFetchEventsRegularly && active) {
    pause();
  }
});

const { show } = useConfirmStore();

const onAddMissingRule = (
  data: Pick<AccountingRuleEntry, 'eventType' | 'eventSubtype' | 'counterparty'>
) => {
  vueRouter.push({
    path: '/settings/accounting',
    query: { 'add-rule': 'true', ...data }
  });
};

const resetPendingDeletion = () => {
  set(eventToDelete, null);
  set(transactionToIgnore, null);
};

const setMissingRulesDialog = (
  event: HistoryEventEntry,
  groupHeader: HistoryEvent
) => {
  set(eventWithMissingRules, event);
  set(selectedGroupEventHeader, groupHeader);
  set(missingRulesDialog, true);
};

const editMissingRulesEntry = (event?: HistoryEventEntry) => {
  if (!event) {
    return;
  }
  const groupHeader = get(selectedGroupEventHeader);
  set(missingRulesDialog, false);
  editEventHandler(event, groupHeader);
};

const showDeleteConfirmation = () => {
  show(
    get(transactionToIgnore)
      ? {
          title: t('transactions.events.confirmation.ignore.title'),
          message: t('transactions.events.confirmation.ignore.message'),
          primaryAction: t('transactions.events.confirmation.ignore.action')
        }
      : {
          title: t('transactions.events.confirmation.delete.title'),
          message: t('transactions.events.confirmation.delete.message'),
          primaryAction: t('common.actions.confirm')
        },
    deleteEventHandler,
    resetPendingDeletion
  );
};

onMounted(async () => {
  await refresh();
});

const refresh = async (userInitiated = false) => {
  const entryTypesVal = get(entryTypes) || [];
  const disableEvmEvents =
    entryTypesVal.length > 0 &&
    !entryTypesVal.includes(HistoryEventEntryType.EVM_EVENT);
  await refreshTransactions(get(onlyChains), disableEvmEvents, userInitiated);
  startPromise(Promise.all([fetchData(), fetchAssociatedLocations()]));
};

onUnmounted(() => {
  pause();
});

watch(eventTaskLoading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});

const {
  setOpenDialog: setTxFormOpenDialog,
  setPostSubmitFunc: setTxFormPostSubmitFunc
} = useHistoryTransactionsForm();

setTxFormPostSubmitFunc(payload => {
  if (payload) {
    fetchDataAndRefreshEvents(payload, true);
  }
});

const addTransactionHash = () => {
  setTxFormOpenDialog(true);
};

const fetchDataAndRefreshEvents = async (
  data: EvmChainAndTxHash,
  reDecodeEvents = false
) => {
  await fetchData();
  if (reDecodeEvents) {
    await forceRedecodeEvmEvents(data);
  }
};

const includeEvmEvents: ComputedRef<boolean> = useEmptyOrSome(
  entryTypes,
  type => isEvmEventType(type)
);

const includeOnlineEvents: ComputedRef<boolean> = useEmptyOrSome(
  entryTypes,
  type => isOnlineHistoryEventType(type)
);

const decodingStatusDialogPersistent: Ref<boolean> = ref(false);
const decodingStatusDialogOpen: Ref<boolean> = ref(false);
const route = useRoute();

watchImmediate(route, async route => {
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
            :disabled="refreshing"
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

      <VDialog
        v-model="decodingStatusDialogOpen"
        max-width="600"
        :persistent="decodingStatusDialogPersistent"
      >
        <HistoryEventsDecodingStatus
          v-if="decodingStatusDialogOpen"
          :refreshing="refreshing"
          @redecode-all-evm-events="redecodeAllEvmEvents()"
        >
          <RuiButton
            variant="text"
            icon
            @click="decodingStatusDialogOpen = false"
          >
            <RuiIcon name="close-line" />
          </RuiButton>
        </HistoryEventsDecodingStatus>
      </VDialog>

      <VMenu offset-y left max-width="200">
        <template #activator="{ on }">
          <RuiBadge
            :value="eventTaskLoading"
            color="primary"
            dot
            placement="top"
            offset-y="12"
            offset-x="-12"
          >
            <RuiButton variant="text" icon size="sm" class="!p-2" v-on="on">
              <RuiIcon name="more-2-fill" />
            </RuiButton>
          </RuiBadge>
        </template>
        <VList>
          <template v-if="includeEvmEvents">
            <RuiButton variant="list" @click="decodingStatusDialogOpen = true">
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
            @click="addTransactionHash()"
          >
            <template #prepend>
              <RuiIcon name="add-line" />
            </template>
            {{ t('transactions.dialog.add_tx') }}
          </RuiButton>
        </VList>
      </VMenu>
    </template>

    <RuiCard>
      <template v-if="!mainPage" #header>
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
              <VSwitch
                v-model="customizedEventsOnly"
                class="mb-4 pt-0 px-4"
                hide-details
                :label="t('transactions.filter.customized_only')"
              />
              <RuiDivider />
              <VSwitch
                v-model="showIgnoredAssets"
                class="mb-4 pt-0 px-4"
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
              <i18n tag="span" path="transactions.filtering_premium_hint">
                <ExternalLink class="!font-bold !text-white" premium>
                  {{ t('common.website') }}
                </ExternalLink>
              </i18n>
            </template>
          </TableFilter>
        </template>

        <HistoryEventsExport :filters="pageParams" />
        <BlockchainAccountSelector
          v-if="!useExternalAccountFilter"
          :value="accounts"
          :chains="txChains"
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

      <CollectionHandler :collection="eventsHeader" @set-page="setPage($event)">
        <template
          #default="{
            data: eventsData,
            itemLength,
            showUpgradeRow,
            limit,
            total,
            found,
            entriesFoundTotal
          }"
        >
          <DataTable
            :expanded="eventsData"
            :headers="tableHeaders"
            :items="eventsData"
            :loading="loading"
            :options="options"
            :server-items-length="itemLength"
            :single-select="false"
            :item-class="getItemClass"
            @update:options="setOptions($event)"
          >
            <template #item.ignoredInAccounting="{ item, isMobile }">
              <IgnoredInAcountingIcon
                v-if="item.ignoredInAccounting"
                class="ml-4"
                :mobile="isMobile"
              />
            </template>
            <template #item.txHash="{ item }">
              <div class="flex items-center gap-2">
                <LocationIcon icon :item="item.location" size="20px" />
                <HistoryEventsIdentifier :event="item" />
              </div>
            </template>
            <template #item.timestamp="{ item }">
              <DateDisplay :timestamp="item.timestamp" milliseconds />
            </template>
            <template #item.action="{ item }">
              <HistoryEventsAction
                :event="item"
                :loading="eventTaskLoading"
                @add-event="addEvent($event)"
                @toggle-ignore="toggleIgnore($event)"
                @redecode="forceRedecodeEvmEvents($event)"
                @reset="resetEvents($event)"
              />
            </template>
            <template #expanded-item="{ headers, item }">
              <HistoryEventsList
                :all-events="allEvents"
                :event-group="item"
                :colspan="headers.length"
                :loading="sectionLoading || eventTaskLoading"
                @edit:event="editEventHandler($event, item)"
                @delete:event="promptForDelete($event)"
                @show:missing-rule-action="setMissingRulesDialog($event, item)"
              />
            </template>
            <template #body.prepend="{ headers }">
              <TransactionQueryStatus
                v-if="includeEvmEvents"
                :only-chains="onlyChains"
                :colspan="headers.length"
              />
              <HistoryEventsQueryStatus
                v-if="includeOnlineEvents"
                :locations="locations"
                :colspan="headers.length"
              />
              <UpgradeRow
                v-if="showUpgradeRow"
                :limit="limit"
                :total="total"
                :found="found"
                :entries-found-total="entriesFoundTotal"
                :colspan="headers.length"
                :label="t('common.events')"
              />
            </template>
          </DataTable>
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
  </TablePageLayout>
</template>
