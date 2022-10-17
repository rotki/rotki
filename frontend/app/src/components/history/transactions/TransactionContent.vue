<template>
  <fragment>
    <card class="mt-8" outlined-body>
      <template #title>
        <refresh-button
          :loading="loading"
          :tooltip="tc('transactions.refresh_tooltip')"
          @refresh="fetch(true)"
        />
        {{ tc('transactions.title') }}
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
              <v-col>
                <div>
                  <blockchain-account-selector
                    v-model="account"
                    :chains="['ETH']"
                    dense
                    :label="tc('transactions.filter.account')"
                    outlined
                    no-padding
                    flat
                  />
                </div>
              </v-col>
            </v-row>
          </v-col>
          <v-col cols="12" md="5">
            <div>
              <table-filter
                :matchers="matchers"
                @update:matches="updateFilter($event)"
              />
            </div>
          </v-col>
        </v-row>
      </template>

      <data-table
        :expanded="data"
        :headers="tableHeaders"
        :items="data"
        :loading="loading || eventTaskLoading"
        :options="options"
        :server-items-length="itemLength"
        :single-select="false"
        :item-class="getItemClass"
        :class="$style.table"
        @update:options="updatePaginationHandler($event)"
      >
        <template #item.ignoredInAccounting="{ item, isMobile }">
          <div v-if="item.ignoredInAccounting" class="pl-4">
            <badge-display v-if="isMobile" color="grey">
              <v-icon small> mdi-eye-off </v-icon>
              <span class="ml-2">
                {{ tc('common.ignored_in_accounting') }}
              </span>
            </badge-display>
            <v-tooltip v-else bottom>
              <template #activator="{ on }">
                <badge-display color="grey" v-on="on">
                  <v-icon small> mdi-eye-off </v-icon>
                </badge-display>
              </template>
              <span>
                {{ tc('common.ignored_in_accounting') }}
              </span>
            </v-tooltip>
          </div>
        </template>
        <template #item.txHash="{ item }">
          <hash-link
            :text="item.txHash"
            :truncate-length="8"
            :full-address="$vuetify.breakpoint.lgAndUp"
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
            <v-menu transition="slide-y-transition" max-width="250px" offset-y>
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
                    <v-icon v-if="item.ignoredInAccounting"> mdi-eye </v-icon>
                    <v-icon v-else> mdi-eye-off </v-icon>
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
            @edit:event="editEventHandler"
            @delete:event="promptForDelete"
          />
        </template>
        <template #body.prepend="{ headers }">
          <transaction-query-status :colspan="headers.length" />
          <upgrade-row
            v-if="showUpgradeRow"
            :limit="limit"
            :total="total"
            :colspan="headers.length"
            :label="tc('transactions.label')"
          />
        </template>
      </data-table>
    </card>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :primary-action="tc('common.actions.save')"
      :action-disabled="!valid"
      :loading="loading"
      @confirm="confirmSave()"
      @cancel="clearDialog()"
    >
      <transaction-event-form
        ref="form"
        v-model="valid"
        :transaction="selectedTransaction"
        :edit="editableItem"
        :save-data="saveData"
      />
    </big-dialog>
    <confirm-dialog
      :display="eventToDelete !== null || transactionToIgnore !== null"
      :title="confirmationTitle"
      confirm-type="warning"
      :message="confirmationMessage"
      :primary-action="confirmationPrimaryAction"
      @cancel="
        eventToDelete = null;
        transactionToIgnore = null;
      "
      @confirm="deleteEventHandler()"
    />
  </fragment>
</template>

<script setup lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { Ref } from 'vue';
import { DataTableHeader } from 'vuetify';
import TransactionEventForm from '@/components/history/TransactionEventForm.vue';
import { isSectionLoading } from '@/composables/common';
import { useTransactionFilter } from '@/composables/filters/transactions';
import { setupIgnore } from '@/composables/history';
import { useTransactions } from '@/store/history/transactions';
import {
  EthTransactionEntry,
  EthTransactionEventEntry,
  IgnoreActionType
} from '@/store/history/types';
import { useTasks } from '@/store/tasks';
import { Collection } from '@/types/collection';
import {
  EthTransaction,
  NewEthTransactionEvent,
  TransactionRequestPayload
} from '@/types/history/tx';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { getCollectionData, setupEntryLimit } from '@/utils/collection';

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof EthTransaction)[];
  sortDesc: boolean[];
};

const Fragment = defineAsyncComponent(
  () => import('@/components/helper/Fragment')
);

const emit = defineEmits(['fetch']);
const fetch = (refresh: boolean = false) => emit('fetch', refresh);

const { tc } = useI18n();

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

const transactionStore = useTransactions();
const { transactions } = storeToRefs(transactionStore);

const { isTaskRunning } = useTasks();

const {
  fetchTransactionEvents,
  updateTransactionsPayload,
  addTransactionEvent,
  editTransactionEvent,
  deleteTransactionEvent
} = transactionStore;

const { data, limit, found, total } = getCollectionData<EthTransactionEntry>(
  transactions as Ref<Collection<EthTransactionEntry>>
);

watch(data, async () => {
  await checkEmptyEvents();
});

const checkEmptyEvents = async () => {
  await fetchTransactionEvents(
    get(data)
      .filter(item => item.decodedEvents!.length === 0)
      .map(item => item.txHash)
  );
};

const redecodeEvents = async (all: boolean = false) => {
  const txHashes = all ? null : get(data).map(item => item.txHash);
  await fetchTransactionEvents(txHashes, true);
};

const forceRedecodeEvents = async (transaction: EthTransactionEntry) => {
  await fetchTransactionEvents([transaction.txHash], true);
};

const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total);

const dialogTitle: Ref<string> = ref('');
const openDialog: Ref<boolean> = ref(false);
const editableItem: Ref<EthTransactionEventEntry | null> = ref(null);
const selectedTransaction: Ref<EthTransactionEntry | null> = ref(null);
const eventToDelete: Ref<EthTransactionEventEntry | null> = ref(null);
const transactionToIgnore: Ref<EthTransactionEntry | null> = ref(null);
const confirmationTitle: Ref<string> = ref('');
const confirmationMessage: Ref<string> = ref('');
const confirmationPrimaryAction: Ref<string> = ref('');
const valid: Ref<boolean> = ref(false);
const form = ref<InstanceType<typeof TransactionEventForm> | null>(null);

const getId = (item: EthTransactionEntry) => item.txHash;

const selected: Ref<EthTransactionEntry[]> = ref([]);

const { filters, matchers, updateFilter } = useTransactionFilter();

const { ignore } = setupIgnore(
  IgnoreActionType.ETH_TRANSACTIONS,
  selected,
  fetch,
  getId
);

const toggleIgnore = async (item: EthTransactionEntry) => {
  set(selected, [item]);
  await ignore(!item.ignoredInAccounting);
};

const addEvent = (item: EthTransactionEntry) => {
  set(selectedTransaction, item);
  set(dialogTitle, tc('transactions.events.dialog.add.title'));
  set(openDialog, true);
};

const editEventHandler = (event: EthTransactionEventEntry) => {
  set(editableItem, event);
  set(dialogTitle, tc('transactions.events.dialog.edit.title'));
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
};

const deleteEventHandler = async () => {
  if (get(transactionToIgnore)) {
    set(selected, [get(transactionToIgnore)]);
    await ignore(true);
  }

  if (get(eventToDelete)?.identifier) {
    const { success } = await deleteTransactionEvent(
      get(eventToDelete)!.identifier!
    );

    if (!success) {
      return;
    }
  }
  set(eventToDelete, null);
  set(transactionToIgnore, null);
  set(confirmationTitle, '');
  set(confirmationMessage, '');
  set(confirmationPrimaryAction, '');
};

const clearDialog = () => {
  get(form)?.reset();

  set(openDialog, false);
  set(editableItem, null);
};

const confirmSave = async () => {
  if (get(form)) {
    const success = await get(form)?.save();
    if (success) {
      clearDialog();
    }
  }
};

const saveData = async (
  event: NewEthTransactionEvent | EthTransactionEventEntry
) => {
  if ((<EthTransactionEventEntry>event).identifier) {
    return await editTransactionEvent(event as EthTransactionEventEntry);
  }
  return await addTransactionEvent(event as NewEthTransactionEvent);
};

const options: Ref<PaginationOptions | null> = ref(null);
const account: Ref<GeneralAccount | null> = ref(null);

const updatePayloadHandler = async () => {
  let paginationOptions = {};
  const optionsVal = get(options);
  if (optionsVal) {
    const { itemsPerPage, page, sortBy, sortDesc } = get(options)!;
    const offset = (page - 1) * itemsPerPage;

    paginationOptions = {
      limit: itemsPerPage,
      offset,
      orderByAttributes: sortBy.length > 0 ? sortBy : ['timestamp'],
      ascending: sortDesc.map(bool => !bool)
    };
  }

  let filterAddress = {};
  if (get(account)) {
    filterAddress = {
      address: get(account)!.address
    };
  }

  const payload: Partial<TransactionRequestPayload> = {
    ...filterAddress,
    ...(get(filters) as Partial<TransactionRequestPayload>),
    ...paginationOptions
  };

  await updateTransactionsPayload(payload);
};

const updatePaginationHandler = async (
  newOptions: PaginationOptions | null
) => {
  set(options, newOptions);
  await updatePayloadHandler();
};

const getItemClass = (item: EthTransactionEntry) =>
  item.ignoredInAccounting ? 'darken-row' : '';

watch(filters, async (filter, oldValue) => {
  if (filter === oldValue) {
    return;
  }

  let newOptions = null;
  if (get(options)) {
    newOptions = {
      ...get(options)!,
      page: 1
    };
  }

  await updatePaginationHandler(newOptions);
});
watch(account, async () => {
  let newOptions = null;
  if (get(options)) {
    newOptions = {
      ...get(options)!,
      page: 1
    };
  }

  await updatePaginationHandler(newOptions);
});

const loading = isSectionLoading(Section.TX);
const eventTaskLoading = isTaskRunning(TaskType.TX_EVENTS);
</script>
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
