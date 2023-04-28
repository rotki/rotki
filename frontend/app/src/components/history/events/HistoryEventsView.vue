<script setup lang="ts">
import { type Account, type GeneralAccount } from '@rotki/common/lib/account';
import {
  type Blockchain,
  type BlockchainSelection
} from '@rotki/common/lib/blockchain';
import isEqual from 'lodash/isEqual';
import { type DataTableHeader } from 'vuetify';
import { not } from '@vueuse/math';
import { type Collection } from '@/types/collection';
import { SavedFilterLocation } from '@/types/filtering';
import { IgnoreActionType } from '@/types/history/ignored';
import {
  type EvmChainAndTxHash,
  type HistoryEvent,
  type HistoryEventEntry,
  type HistoryEventRequestPayload
} from '@/types/history/events';
import { RouterAccountsSchema } from '@/types/route';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { type Writeable } from '@/types';
import { isValidTxHash } from '@/utils/text';
import { toEvmChainAndTxHash } from '@/utils/history';
import type { Filters, Matcher } from '@/composables/filters/events';

const props = withDefaults(
  defineProps<{
    location?: string;
    protocols?: string[];
    eventTypes?: string[];
    eventSubTypes?: string[];
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
    externalAccountFilter: () => [],
    useExternalAccountFilter: false,
    sectionTitle: '',
    mainPage: false,
    onlyChains: () => []
  }
);

const { tc } = useI18n();

const {
  location,
  protocols,
  useExternalAccountFilter,
  externalAccountFilter,
  sectionTitle,
  eventTypes,
  eventSubTypes,
  mainPage,
  onlyChains
} = toRefs(props);

const editableItem: Ref<HistoryEventEntry | null> = ref(null);
const selectedTransaction: Ref<HistoryEventEntry | null> = ref(null);
const eventToDelete: Ref<HistoryEventEntry | null> = ref(null);
const transactionToIgnore: Ref<HistoryEventEntry | null> = ref(null);
const confirmationTitle: Ref<string> = ref('');
const confirmationPrimaryAction: Ref<string> = ref('');
const accounts: Ref<GeneralAccount[]> = ref([]);

const usedTitle: ComputedRef<string> = computed(
  () => get(sectionTitle) || tc('transactions.title')
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
    text: tc('transactions.events.headers.event_identifier'),
    value: 'txHash',
    sortable: false
  },
  {
    text: tc('common.datetime'),
    value: 'timestamp',
    cellClass: 'text-no-wrap'
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

const {
  refreshTransactions,
  fetchTransactionEvents,
  deleteTransactionEvent,
  fetchHistoryEvents
} = useHistoryEvents();

const {
  options,
  selected,
  openDialog,
  confirmationMessage,
  isLoading: isEventsGroupHeaderLoading,
  userAction,
  state: eventsHeader,
  filters,
  matchers,
  setPage,
  setOptions,
  setFilter,
  updateFilter,
  fetchData
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
    useHistoryEventFilter({
      protocols: get(protocols).length > 0,
      locations: !!get(location)
    }),
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
      )
    })),
    customPageParams: computed<Partial<HistoryEventRequestPayload>>(() => {
      const params: Writeable<Partial<HistoryEventRequestPayload>> = {
        counterparties: get(protocols),
        eventTypes: get(eventTypes),
        eventSubtypes: get(eventSubTypes),
        groupByEventIds: true
      };

      const accounts = get(usedAccounts);

      if (isDefined(location)) {
        params.location = get(location);
      }

      if (accounts.length > 0) {
        const firstAccount = accounts[0];

        if (firstAccount.chain !== 'ALL') {
          params.location = getEvmChainName(firstAccount.chain)!;
        }

        params.locationLabels = accounts.map(({ address }) => address);
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
      groupByEventIds: false
    });

    return response.data;
  },
  [],
  {
    lazy: true,
    evaluating: isEventsLoading
  }
);

const onFilterAccountsChanged = (acc: Account<BlockchainSelection>[]) => {
  set(userAction, true);
  set(accounts, acc.length > 0 ? [acc[0]] : []);
};

const redecodeEvents = async (all = false) => {
  const txHashes = all
    ? null
    : get(data).map(item => toEvmChainAndTxHash(item));
  await fetchTransactionEvents(txHashes, true);
};

const forceRedecodeTxEvents = async (data: EvmChainAndTxHash) => {
  await fetchTransactionEvents([data], true);
};

const { ignore } = useIgnore<HistoryEventEntry>(
  {
    actionType: IgnoreActionType.EVM_TRANSACTIONS,
    toData: (item: HistoryEventEntry) => toEvmChainAndTxHash(item)
  },
  selected,
  fetchData
);

const toggleIgnore = async (item: HistoryEventEntry) => {
  set(selected, [item]);
  await ignore(!item.ignoredInAccounting);
};

const addEvent = (tx: HistoryEventEntry) => {
  set(selectedTransaction, tx);
  set(editableItem, null);
  set(openDialog, true);
};

const editEventHandler = (event: HistoryEventEntry, tx: HistoryEventEntry) => {
  set(selectedTransaction, tx);
  set(editableItem, event);
  set(openDialog, true);
};

const promptForDelete = ({
  item,
  canDelete
}: {
  item: HistoryEventEntry;
  canDelete: boolean;
}) => {
  if (canDelete) {
    set(confirmationTitle, tc('transactions.events.confirmation.delete.title'));
    set(
      confirmationMessage,
      tc('transactions.events.confirmation.delete.message')
    );
    set(confirmationPrimaryAction, tc('common.actions.confirm'));
    set(eventToDelete, item);
  } else {
    set(confirmationTitle, tc('transactions.events.confirmation.ignore.title'));
    set(
      confirmationMessage,
      tc('transactions.events.confirmation.ignore.message')
    );
    set(
      confirmationPrimaryAction,
      tc('transactions.events.confirmation.ignore.action')
    );
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
    const { success } = await deleteTransactionEvent(id);
    if (!success) {
      return;
    }
    await fetchDataAndRefreshEvents(toEvmChainAndTxHash(eventToDeleteVal));
  }

  set(eventToDelete, null);
  set(transactionToIgnore, null);
  set(confirmationTitle, '');
  set(confirmationMessage, '');
  set(confirmationPrimaryAction, '');
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

    // Because the evmChain filter and the account filter can't be active
    // at the same time we clear the account filter when the evmChain filter
    // is set.
    if (filterChanged && filters.location) {
      set(accounts, []);
    }

    if (accountsChanged && usedAccounts.length > 0) {
      const updatedFilter = { ...get(filters) };
      delete updatedFilter.location;
      updateFilter(updatedFilter);
    }

    if (filterChanged || accountsChanged) {
      set(options, { ...get(options), page: 1 });
    }
  }
);

const { isLoading: isSectionLoading } = useStatusStore();
const sectionLoading = isSectionLoading(Section.TX);

const eventTaskLoading = isTaskRunning(TaskType.TX_EVENTS);
const { isAllFinished: isQueryingTxsFinished } = toRefs(
  useTxQueryStatusStore()
);

const shouldFetchEventsRegularly = logicOr(
  sectionLoading,
  not(isQueryingTxsFinished),
  eventTaskLoading
);

const anyLoading = logicOr(
  shouldFetchEventsRegularly,
  isEventsGroupHeaderLoading,
  isEventsLoading
);

const { pause, resume, isActive } = useIntervalFn(() => {
  fetchData();
}, 10000);

watch(shouldFetchEventsRegularly, shouldFetchEventsRegularly => {
  const active = get(isActive);
  if (shouldFetchEventsRegularly && !active) {
    resume();
  } else if (!shouldFetchEventsRegularly && active) {
    pause();
  }
});

const { show } = useConfirmStore();

const resetPendingDeletion = () => {
  set(eventToDelete, null);
  set(transactionToIgnore, null);
};

const showDeleteConfirmation = () => {
  show(
    {
      title: get(confirmationTitle),
      message: get(confirmationMessage),
      primaryAction: get(confirmationPrimaryAction)
    },
    deleteEventHandler,
    resetPendingDeletion
  );
};

const { txEvmChains, getEvmChainName, getChain } = useSupportedChains();
const txChains = useArrayMap(txEvmChains, x => x.id);

onMounted(async () => {
  await fetchData();
  await refreshTransactions(get(onlyChains));
});

onUnmounted(() => {
  pause();
});

watch(eventTaskLoading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});

const openAddTxDialog: Ref<boolean> = ref(false);
const addTransactionHash = () => {
  set(openAddTxDialog, true);
};

const fetchDataAndRefreshEvents = async (
  data: EvmChainAndTxHash,
  reDecodeEvents = false
) => {
  await fetchData();
  if (reDecodeEvents) {
    await forceRedecodeTxEvents(data);
  }
};
</script>

<template>
  <div>
    <card class="mt-8" outlined-body>
      <v-btn
        v-if="mainPage"
        absolute
        fab
        top
        right
        dark
        color="primary"
        data-cy="ledger-actions__add"
        @click="addTransactionHash()"
      >
        <v-icon>mdi-plus</v-icon>
      </v-btn>
      <template #title>
        <refresh-button
          :loading="sectionLoading"
          :tooltip="tc('transactions.refresh_tooltip')"
          @refresh="refreshTransactions(onlyChains, true)"
        />
        {{ usedTitle }}
      </template>
      <template #actions>
        <v-row>
          <v-col cols="12" md="7">
            <v-row>
              <v-col cols="auto">
                <v-menu offset-y>
                  <template #activator="{ on }">
                    <v-btn color="primary" depressed height="40px" v-on="on">
                      {{ tc('transactions.redecode_events.title') }}
                    </v-btn>
                  </template>
                  <v-list>
                    <v-list-item link @click="redecodeEvents()">
                      <v-list-item-title>
                        {{ tc('transactions.redecode_events.this_page') }}
                      </v-list-item-title>
                    </v-list-item>
                    <v-list-item link @click="redecodeEvents(true)">
                      <v-list-item-title>
                        {{ tc('transactions.redecode_events.all') }}
                      </v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-menu>
              </v-col>
              <v-col v-if="!useExternalAccountFilter">
                <div>
                  <blockchain-account-selector
                    :value="accounts"
                    :chains="txChains"
                    dense
                    :label="tc('transactions.filter.account')"
                    outlined
                    no-padding
                    multichain
                    flat
                    @input="onFilterAccountsChanged($event)"
                  />
                </div>
              </v-col>
            </v-row>
          </v-col>
          <v-col cols="12" md="5">
            <div>
              <table-filter
                :matches="filters"
                :matchers="matchers"
                :location="SavedFilterLocation.HISTORY_EVENTS"
                @update:matches="setFilter($event)"
              />
            </div>
          </v-col>
        </v-row>
      </template>

      <collection-handler
        :collection="eventsHeader"
        @set-page="setPage($event)"
      >
        <template
          #default="{
            data: eventsData,
            itemLength,
            showUpgradeRow,
            limit,
            total
          }"
        >
          <data-table
            :expanded="eventsData"
            :headers="tableHeaders"
            :items="eventsData"
            :loading="anyLoading"
            :options="options"
            :server-items-length="itemLength"
            :single-select="false"
            :item-class="getItemClass"
            :class="$style.table"
            @update:options="setOptions($event)"
          >
            <template #item.ignoredInAccounting="{ item, isMobile }">
              <div v-if="item.tx?.ignoredInAccounting" class="pl-4">
                <badge-display v-if="isMobile" color="grey">
                  <v-icon small> mdi-eye-off</v-icon>
                  <span class="ml-2">
                    {{ tc('common.ignored_in_accounting') }}
                  </span>
                </badge-display>
                <v-tooltip v-else bottom>
                  <template #activator="{ on }">
                    <badge-display color="grey" v-on="on">
                      <v-icon small> mdi-eye-off</v-icon>
                    </badge-display>
                  </template>
                  <span>
                    {{ tc('common.ignored_in_accounting') }}
                  </span>
                </v-tooltip>
              </div>
            </template>
            <template #item.txHash="{ item }">
              <div class="d-flex">
                <div class="mr-2">
                  <adaptive-wrapper>
                    <evm-chain-icon size="20" tooltip :chain="item.location" />
                  </adaptive-wrapper>
                </div>
                <hash-link
                  :no-link="!isValidTxHash(item.eventIdentifier)"
                  :text="item.eventIdentifier"
                  :truncate-length="8"
                  :full-address="$vuetify.breakpoint.lgAndUp"
                  :chain="getChain(item.location)"
                  tx
                />
              </div>
            </template>
            <template #item.timestamp="{ item }">
              <date-display :timestamp="item.timestamp" />
            </template>
            <template #item.action="{ item }">
              <div class="d-flex align-center">
                <v-menu
                  transition="slide-y-transition"
                  max-width="250px"
                  offset-y
                >
                  <template #activator="{ on }">
                    <v-btn class="ml-1" icon v-on="on">
                      <v-icon>mdi-dots-vertical</v-icon>
                    </v-btn>
                  </template>
                  <v-list>
                    <v-list-item link @click="addEvent(item)">
                      <v-list-item-icon class="mr-4">
                        <v-icon>mdi-plus</v-icon>
                      </v-list-item-icon>
                      <v-list-item-content>
                        {{ tc('transactions.actions.add_event') }}
                      </v-list-item-content>
                    </v-list-item>
                    <v-list-item
                      v-if="isValidTxHash(item.eventIdentifier)"
                      link
                      @click="toggleIgnore(item)"
                    >
                      <v-list-item-icon class="mr-4">
                        <v-icon v-if="item.ignoredInAccounting">
                          mdi-eye
                        </v-icon>
                        <v-icon v-else> mdi-eye-off</v-icon>
                      </v-list-item-icon>
                      <v-list-item-content>
                        {{
                          item.ignoredInAccounting
                            ? tc('transactions.unignore')
                            : tc('transactions.ignore')
                        }}
                      </v-list-item-content>
                    </v-list-item>
                    <v-list-item
                      v-if="isValidTxHash(item.eventIdentifier)"
                      link
                      :disabled="eventTaskLoading"
                      @click="forceRedecodeTxEvents(toEvmChainAndTxHash(item))"
                    >
                      <v-list-item-icon class="mr-4">
                        <v-icon>mdi-database-refresh</v-icon>
                      </v-list-item-icon>
                      <v-list-item-content>
                        {{ tc('transactions.actions.redecode_events') }}
                      </v-list-item-content>
                    </v-list-item>
                  </v-list>
                </v-menu>
              </div>
            </template>
            <template #expanded-item="{ headers, item }">
              <history-events-list
                :all-events="allEvents"
                :event-group-header="item"
                :colspan="headers.length"
                :show-event-detail="protocols.length > 0"
                :loading="sectionLoading || eventTaskLoading"
                @edit:event="editEventHandler($event, item)"
                @delete:event="promptForDelete($event)"
              />
            </template>
            <template #body.prepend="{ headers }">
              <transaction-query-status
                :only-chains="onlyChains"
                :colspan="headers.length"
              />
              <upgrade-row
                v-if="showUpgradeRow"
                :limit="limit"
                :total="total"
                :colspan="headers.length"
                :label="tc('transactions.label')"
              />
            </template>
          </data-table>
        </template>
      </collection-handler>
    </card>

    <history-event-form-dialog
      v-model="openDialog"
      :loading="sectionLoading"
      :editable-item="editableItem"
      :open="openDialog"
      :transaction="selectedTransaction"
      @reset-edit="editableItem = null"
      @saved="fetchDataAndRefreshEvents($event)"
    />

    <history-form-dialog
      v-model="openAddTxDialog"
      :loading="sectionLoading"
      @saved="fetchDataAndRefreshEvents($event, true)"
    />
  </div>
</template>

<style module lang="scss">
.table {
  :global {
    .v-data-table {
      &__expanded {
        &__content {
          td {
            &:first-child {
              padding-left: 0 !important;
              padding-right: 0 !important;
            }
          }
        }
      }
    }
  }
}
</style>
