<template>
  <fragment>
    <card class="mt-8" outlined-body>
      <template #title>
        <refresh-button
          :loading="loading"
          :tooltip="$t('transactions.refresh_tooltip')"
          @refresh="fetch(true)"
        />
        {{ $t('transactions.title') }}
      </template>
      <template #actions>
        <v-row justify="end">
          <v-col v-if="isDevelopment" cols="12" md="6">
            <div>
              <v-btn color="primary" @click="redecodeAllEvents">
                {{ $t('transactions.redecode_all_events') }}
              </v-btn>
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div>
              <blockchain-account-selector
                v-model="account"
                :chains="['ETH']"
                dense
                :label="$t('transactions.filter.label')"
                outlined
                no-padding
                flat
              />
            </div>
          </v-col>
        </v-row>
      </template>

      <data-table
        :expanded="data"
        :headers="tableHeaders"
        :items="data"
        :loading="loading"
        :options="options"
        :server-items-length="itemLength"
        :single-select="false"
        :mobile-breakpoint="0"
        :item-class="item => (item.ignoredInAccounting ? 'darken-row' : '')"
        item-key="identifier"
        :class="$style.table"
        @update:options="updatePaginationHandler($event)"
      >
        <template #item.ignoredInAccounting="{ item, isMobile }">
          <div v-if="item.ignoredInAccounting" class="pl-4">
            <badge-display v-if="isMobile" color="grey">
              <v-icon small> mdi-eye-off </v-icon>
              <span class="ml-2">
                {{ $t('transactions.headers.ignored') }}
              </span>
            </badge-display>
            <v-tooltip v-else bottom>
              <template #activator="{ on }">
                <badge-display color="grey" v-on="on">
                  <v-icon small> mdi-eye-off </v-icon>
                </badge-display>
              </template>
              <span>
                {{ $t('transactions.headers.ignored') }}
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
            {{ $t('transactions.details.internal_transaction') }}
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
                  {{ $t('transactions.actions.details') }}
                  <v-icon small>mdi-chevron-right</v-icon>
                </v-btn>
              </template>

              <transaction-detail :transaction="item" />
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
                    {{ $t('transactions.actions.add_event') }}
                  </v-list-item-content>
                </v-list-item>
                <v-list-item link @click="toggleIgnore(item)">
                  <v-list-item-icon class="mr-4">
                    <v-icon v-if="item.ignoredInAccounting">
                      mdi-eye-off
                    </v-icon>
                    <v-icon v-else> mdi-eye </v-icon>
                  </v-list-item-icon>
                  <v-list-item-content>
                    {{
                      item.ignoredInAccounting
                        ? $t('transactions.unignore')
                        : $t('transactions.ignore')
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
                    {{ $t('transactions.actions.redecode_events') }}
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
            @edit:event="event => editEventHandler(event)"
            @delete:event="event => promptForDelete(item, event)"
          />
        </template>
        <template v-if="showUpgradeRow" #body.prepend="{ headers }">
          <upgrade-row
            :limit="limit"
            :total="total"
            :colspan="headers.length"
            :label="$t('transactions.label')"
          />
        </template>
      </data-table>
    </card>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :primary-action="$t('transactions.events.dialog.save')"
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

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { defineComponent, Ref, ref, unref, watch } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import Fragment from '@/components/helper/Fragment';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import TransactionEventForm, {
  TransactionEventFormInstance
} from '@/components/history/TransactionEventForm.vue';
import TransactionDetail from '@/components/history/transactions/TransactionDetail.vue';
import TransactionEvents from '@/components/history/transactions/TransactionEvents.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { isSectionLoading } from '@/composables/common';
import {
  getCollectionData,
  setupEntryLimit,
  setupIgnore
} from '@/composables/history';
import i18n from '@/i18n';
import {
  EthTransaction,
  NewEthTransactionEvent,
  TransactionRequestPayload
} from '@/services/history/types';
import { Section } from '@/store/const';
import { useTransactions } from '@/store/history';
import {
  EthTransactionEntry,
  EthTransactionEventEntry,
  IgnoreActionType
} from '@/store/history/types';
import { useTasks } from '@/store/tasks';
import { Collection } from '@/types/collection';
import { TaskType } from '@/types/task-type';

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof EthTransaction)[];
  sortDesc: boolean[];
};

const tableHeaders: DataTableHeader[] = [
  {
    text: '',
    value: 'ignoredInAccounting',
    sortable: false,
    class: 'pa-0',
    cellClass: 'pa-0',
    width: '0px'
  },
  {
    text: i18n.t('transactions.headers.tx_hash').toString(),
    value: 'txHash',
    sortable: false
  },
  {
    text: i18n.t('transactions.headers.timestamp').toString(),
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
];

const isDevelopment = process.env.NODE_ENV === 'development';

export default defineComponent({
  name: 'TransactionContent',
  components: {
    Fragment,
    TransactionEventForm,
    BigDialog,
    TransactionDetail,
    BadgeDisplay,
    UpgradeRow,
    TransactionEvents,
    BlockchainAccountSelector,
    RefreshButton
  },
  emits: ['fetch'],
  setup(_, { emit }) {
    const fetch = (refresh: boolean = false) => emit('fetch', refresh);

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

    const { data, limit, found, total } =
      getCollectionData<EthTransactionEntry>(
        transactions as Ref<Collection<EthTransactionEntry>>
      );

    watch(data, () => {
      checkEmptyEvents();
    });

    const checkEmptyEvents = async () => {
      await fetchTransactionEvents(
        unref(data)
          .filter(item => item.decodedEvents!.length === 0)
          .map(item => item.txHash)
      );
    };

    const redecodeAllEvents = async () => {
      await fetchTransactionEvents(
        unref(data).map(item => item.txHash),
        true
      );
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
    const form = ref<TransactionEventFormInstance | null>(null);

    const getId = (item: EthTransactionEntry) => item.identifier;

    const selected: Ref<EthTransactionEntry[]> = ref([]);

    const { ignore } = setupIgnore(
      IgnoreActionType.ETH_TRANSACTIONS,
      selected,
      data,
      fetch,
      getId
    );

    const toggleIgnore = (item: EthTransactionEntry) => {
      selected.value = [item];
      ignore(!item.ignoredInAccounting);
    };

    const addEvent = (item: EthTransactionEntry) => {
      selectedTransaction.value = item;
      dialogTitle.value = i18n
        .t('transactions.events.dialog.add.title')
        .toString();
      openDialog.value = true;
    };

    const editEventHandler = (event: EthTransactionEventEntry) => {
      editableItem.value = event;
      dialogTitle.value = i18n
        .t('transactions.events.dialog.edit.title')
        .toString();
      openDialog.value = true;
    };

    const promptForDelete = (
      item: EthTransactionEntry,
      event: EthTransactionEventEntry
    ) => {
      const canDelete = item.decodedEvents!.length > 1;

      if (canDelete) {
        confirmationTitle.value = i18n
          .t('transactions.events.confirmation.delete.title')
          .toString();
        confirmationMessage.value = i18n
          .t('transactions.events.confirmation.delete.message')
          .toString();
        confirmationPrimaryAction.value = i18n
          .t('transactions.events.confirmation.delete.action')
          .toString();
        eventToDelete.value = event;
      } else {
        confirmationTitle.value = i18n
          .t('transactions.events.confirmation.ignore.title')
          .toString();
        confirmationMessage.value = i18n
          .t('transactions.events.confirmation.ignore.message')
          .toString();
        confirmationPrimaryAction.value = i18n
          .t('transactions.events.confirmation.ignore.action')
          .toString();
        transactionToIgnore.value = item;
      }
    };

    const deleteEventHandler = async () => {
      if (transactionToIgnore.value) {
        selected.value = [transactionToIgnore.value];
        ignore(true);
      }

      if (eventToDelete.value?.identifier) {
        const { success } = await deleteTransactionEvent(
          eventToDelete.value.identifier
        );

        if (!success) {
          return;
        }
      }
      eventToDelete.value = null;
      transactionToIgnore.value = null;
      confirmationTitle.value = '';
      confirmationMessage.value = '';
      confirmationPrimaryAction.value = '';
    };

    const clearDialog = () => {
      form.value?.reset();

      openDialog.value = false;
      editableItem.value = null;
    };

    const confirmSave = async () => {
      if (form.value) {
        const success = await form.value?.save();
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

    const updatePayloadHandler = () => {
      let paginationOptions = {};
      if (options.value) {
        options.value = {
          ...options.value,
          sortBy:
            options.value.sortBy.length > 0 ? [options.value.sortBy[0]] : [],
          sortDesc:
            options.value.sortDesc.length > 0 ? [options.value.sortDesc[0]] : []
        };

        const { itemsPerPage, page, sortBy, sortDesc } = options.value;
        const offset = (page - 1) * itemsPerPage;

        paginationOptions = {
          limit: itemsPerPage,
          offset,
          orderByAttribute: sortBy.length > 0 ? sortBy[0] : 'timestamp',
          ascending: !sortDesc[0]
        };
      }

      let filterAddress = {};
      if (account.value) {
        filterAddress = {
          address: account.value?.address
        };
      }
      const payload: Partial<TransactionRequestPayload> = {
        ...filterAddress,
        ...paginationOptions
      };

      updateTransactionsPayload(payload);
    };

    const updatePaginationHandler = (newOptions: PaginationOptions | null) => {
      options.value = newOptions;
      updatePayloadHandler();
    };

    watch(account, () => {
      let newOptions = null;
      if (options.value) {
        newOptions = {
          ...options.value,
          page: 1
        };
      }

      updatePaginationHandler(newOptions);
    });

    const loading = isSectionLoading(Section.TX);
    const eventTaskLoading = isTaskRunning(TaskType.TX_EVENTS);

    return {
      isDevelopment,
      account,
      tableHeaders,
      data,
      limit,
      found,
      total,
      itemLength,
      fetch,
      showUpgradeRow,
      loading,
      eventTaskLoading,
      dialogTitle,
      openDialog,
      editableItem,
      selectedTransaction,
      eventToDelete,
      transactionToIgnore,
      confirmationTitle,
      confirmationMessage,
      confirmationPrimaryAction,
      valid,
      addEvent,
      editEventHandler,
      promptForDelete,
      deleteEventHandler,
      form,
      clearDialog,
      confirmSave,
      saveData,
      options,
      updatePaginationHandler,
      toggleIgnore,
      forceRedecodeEvents,
      redecodeAllEvents
    };
  }
});
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
