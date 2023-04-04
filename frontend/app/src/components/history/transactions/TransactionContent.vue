<script setup lang="ts">
import { type Account, type GeneralAccount } from '@rotki/common/lib/account';
import {
  type Blockchain,
  type BlockchainSelection
} from '@rotki/common/lib/blockchain';
import {
  type HistoryEventSubType,
  type HistoryEventType,
  type TransactionEventProtocol
} from '@rotki/common/lib/history/tx-events';
import isEqual from 'lodash/isEqual';
import { type ComputedRef, type Ref } from 'vue';
import { type DataTableHeader } from 'vuetify';
import { SavedFilterLocation } from '@/types/filtering';
import { IgnoreActionType } from '@/types/history/ignored';
import {
  type EthTransaction,
  type EthTransactionEntry,
  type EthTransactionEventEntry,
  type EvmChainAddress,
  type TransactionRequestPayload
} from '@/types/history/tx';
import { RouterAccountsSchema } from '@/types/route';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { getCollectionData } from '@/utils/collection';
import type { Filters, Matcher } from '@/composables/filters/transactions';

const props = withDefaults(
  defineProps<{
    protocols?: TransactionEventProtocol[];
    eventTypes?: HistoryEventType[];
    eventSubTypes?: HistoryEventSubType[];
    externalAccountFilter?: Account[];
    useExternalAccountFilter?: boolean;
    sectionTitle?: string;
    mainPage?: boolean;
    onlyChains?: Blockchain[];
  }>(),
  {
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
  protocols,
  useExternalAccountFilter,
  externalAccountFilter,
  sectionTitle,
  eventTypes,
  eventSubTypes,
  mainPage,
  onlyChains
} = toRefs(props);

const editableItem: Ref<EthTransactionEventEntry | null> = ref(null);
const selectedTransaction: Ref<EthTransactionEntry | null> = ref(null);
const eventToDelete: Ref<EthTransactionEventEntry | null> = ref(null);
const transactionToIgnore: Ref<EthTransactionEntry | null> = ref(null);
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
    return get(accounts);
  }
);

const filteredAccounts: ComputedRef<EvmChainAddress[]> = computed(() => {
  const accounts = get(usedAccounts);

  if (accounts.length === 0) {
    return [];
  }

  const filterAccounts: EvmChainAddress[] = [];

  accounts.forEach(account => {
    if (account.chain === 'ALL') {
      const chains = get(txEvmChains);
      chains.forEach(chain => {
        filterAccounts.push({
          address: account.address,
          evmChain: chain.evmChainName
        });
      });
    } else {
      filterAccounts.push({
        address: account.address,
        evmChain: getEvmChainName(account.chain)!
      });
    }
  });

  return filterAccounts;
});

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
    text: tc('common.tx_hash'),
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
  fetchTransactions,
  refreshTransactions,
  fetchTransactionEvents,
  deleteTransactionEvent
} = useTransactions();

const {
  options,
  selected,
  openDialog,
  confirmationMessage,
  isLoading,
  userAction,
  state: transactions,
  filters,
  matchers,
  setPage,
  setOptions,
  setFilter,
  updateFilter,
  fetchData
} = useHistoryPaginationFilter<
  EthTransaction,
  TransactionRequestPayload,
  EthTransactionEntry,
  Filters,
  Matcher
>(
  null,
  mainPage,
  () => useTransactionFilter(get(protocols).length > 0),
  fetchTransactions,
  {
    onUpdateFilters(query) {
      const parsedAccounts = RouterAccountsSchema.parse(query);
      set(accounts, parsedAccounts.accounts ?? []);
    },
    extraParams: computed(() => ({
      accounts: get(usedAccounts).map(
        account => `${account.address}#${account.chain}`
      )
    })),
    customPageParams: computed<Partial<TransactionRequestPayload>>(() => ({
      protocols: get(protocols),
      eventTypes: get(eventTypes),
      eventSubtypes: get(eventSubTypes),
      accounts: get(filteredAccounts)
    }))
  }
);

const { data } = getCollectionData<EthTransactionEntry>(transactions);

const redecodeEvents = async (all = false) => {
  const txHashes = all ? null : get(data);
  await fetchTransactionEvents(txHashes, true);
};

const forceRedecodeEvents = async (transaction: EthTransactionEntry) => {
  await fetchTransactionEvents([transaction], true);
};

const { ignore } = useIgnore(
  {
    actionType: IgnoreActionType.EVM_TRANSACTIONS,
    toData: (item: EthTransactionEntry) => ({
      txHash: item.txHash,
      evmChain: item.evmChain
    })
  },
  selected,
  fetchData
);

const toggleIgnore = async (item: EthTransactionEntry) => {
  set(selected, [item]);
  await ignore(!item.ignoredInAccounting);
};

const addEvent = (item: EthTransactionEntry) => {
  set(selectedTransaction, item);
  set(editableItem, null);
  set(openDialog, true);
};

const editEventHandler = (event: EthTransactionEventEntry) => {
  set(editableItem, event);
  set(openDialog, true);
};

const promptForDelete = ({
  txEvent,
  tx
}: {
  tx: EthTransactionEntry;
  txEvent: EthTransactionEventEntry;
}) => {
  const canDelete = tx.decodedEvents!.length > 1;

  if (canDelete) {
    set(confirmationTitle, tc('transactions.events.confirmation.delete.title'));
    set(
      confirmationMessage,
      tc('transactions.events.confirmation.delete.message')
    );
    set(confirmationPrimaryAction, tc('common.actions.confirm'));
    set(eventToDelete, txEvent);
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
    set(transactionToIgnore, tx);
  }
  showDeleteConfirmation();
};

const deleteEventHandler = async () => {
  const txToIgnore = get(transactionToIgnore);
  if (txToIgnore) {
    set(selected, [txToIgnore]);
    await ignore(true);
  }

  const id = get(eventToDelete)?.identifier;

  if (id) {
    const { success } = await deleteTransactionEvent(id);
    if (!success) {
      return;
    }
    await fetchData();
  }

  set(eventToDelete, null);
  set(transactionToIgnore, null);
  set(confirmationTitle, '');
  set(confirmationMessage, '');
  set(confirmationPrimaryAction, '');
};

const getItemClass = (item: EthTransactionEntry) =>
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
    if (filterChanged && filters.evmChain) {
      set(accounts, []);
    }

    if (accountsChanged && usedAccounts.length > 0) {
      const updatedFilter = { ...get(filters) };
      delete updatedFilter.evmChain;
      updateFilter(updatedFilter);
    }

    if (filterChanged || accountsChanged) {
      set(options, { ...get(options), page: 1 });
    }
  }
);

const { isLoading: isSectionLoading } = useStatusStore();
const loading = isSectionLoading(Section.TX);

const eventTaskLoading = isTaskRunning(TaskType.TX_EVENTS);
const { isAllFinished } = toRefs(useTxQueryStatusStore());

const { pause, resume, isActive } = useIntervalFn(fetchData, 10000);

watch(
  [loading, eventTaskLoading, isAllFinished],
  ([sectionLoading, eventTaskLoading, isAllFinished]) => {
    if (
      (sectionLoading || eventTaskLoading || !isAllFinished) &&
      !get(isActive)
    ) {
      resume();
    } else if (
      !sectionLoading &&
      !eventTaskLoading &&
      isAllFinished &&
      get(isActive)
    ) {
      pause();
    }
  }
);

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

watch(loading, async (isLoading, wasLoading) => {
  if (!isLoading && wasLoading) {
    await fetchData();
  }
});

const openAddTxDialog: Ref<boolean> = ref(false);
const addTransactionHash = () => {
  set(openAddTxDialog, true);
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
          :loading="loading"
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
                    v-model="accounts"
                    :chains="txChains"
                    dense
                    multiple
                    :label="tc('transactions.filter.account')"
                    outlined
                    no-padding
                    multichain
                    flat
                    @input="userAction = true"
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
                :location="SavedFilterLocation.HISTORY_TRANSACTIONS"
                @update:matches="setFilter($event)"
              />
            </div>
          </v-col>
        </v-row>
      </template>

      <collection-handler :collection="transactions" @set-page="setPage">
        <template #default="{ itemLength, showUpgradeRow, limit, total }">
          <data-table
            :expanded="data"
            :headers="tableHeaders"
            :items="data"
            :loading="isLoading"
            :options="options"
            :server-items-length="itemLength"
            :single-select="false"
            :item-class="getItemClass"
            :class="$style.table"
            @update:options="setOptions($event)"
          >
            <template #item.ignoredInAccounting="{ item, isMobile }">
              <div v-if="item.ignoredInAccounting" class="pl-4">
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
                    <evm-chain-icon size="20" tooltip :chain="item.evmChain" />
                  </adaptive-wrapper>
                </div>
                <hash-link
                  :text="item.txHash"
                  :truncate-length="8"
                  :full-address="$vuetify.breakpoint.lgAndUp"
                  :chain="getChain(item.evmChain)"
                  tx
                />
                <v-chip
                  v-if="item.gasPrice.lt(0)"
                  small
                  text-color="white"
                  color="accent"
                  class="mb-1 mt-1"
                >
                  {{ tc('transactions.details.internal_transaction') }}
                </v-chip>
              </div>
            </template>
            <template #item.timestamp="{ item }">
              <date-display :timestamp="item.timestamp" />
            </template>
            <template #item.action="{ item }">
              <div class="d-flex align-center">
                <v-dialog width="600">
                  <template #activator="{ on }">
                    <v-btn small color="primary" text v-on="on">
                      {{ tc('common.details') }}
                      <v-icon small>mdi-chevron-right</v-icon>
                    </v-btn>
                  </template>

                  <template #default="dialog">
                    <transaction-detail
                      :transaction="item"
                      @close="dialog.value = false"
                    />
                  </template>
                </v-dialog>
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
                    <v-list-item link @click="toggleIgnore(item)">
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
                      link
                      :disabled="eventTaskLoading"
                      @click="forceRedecodeEvents(item)"
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
              <transaction-events
                :transaction="item"
                :colspan="headers.length"
                :show-event-detail="protocols.length > 0"
                :loading="loading || eventTaskLoading"
                @edit:event="editEventHandler"
                @delete:event="promptForDelete"
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
    <transaction-event-form-dialog
      v-model="openDialog"
      :loading="loading"
      :editable-item="editableItem"
      :open="openDialog"
      :transaction="selectedTransaction"
      @reset-edit="editableItem = null"
      @saved="fetchData()"
    />

    <transaction-form-dialog
      v-model="openAddTxDialog"
      :loading="loading"
      @saved="fetchData()"
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
