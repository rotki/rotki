<template>
  <fragment>
    <card class="mt-8" outlined-body>
      <template #title>
        <refresh-button
          :loading="loading"
          :tooltip="$tc('transactions.refresh_tooltip')"
          @refresh="fetch(true)"
        />
        {{ $t('transactions.title') }}
      </template>
      <template #actions>
        <v-row>
          <v-col cols="12" md="6">
            <v-row>
              <v-col cols="auto">
                <v-menu offset-y>
                  <template #activator="{ on }">
                    <v-btn color="primary" depressed v-on="on">
                      {{ $t('transactions.redecode_events.title') }}
                    </v-btn>
                  </template>
                  <v-list>
                    <v-list-item link @click="redecodeEvents()">
                      <v-list-item-title>
                        {{ $t('transactions.redecode_events.this_page') }}
                      </v-list-item-title>
                    </v-list-item>
                    <v-list-item link @click="redecodeEvents(true)">
                      <v-list-item-title>
                        {{ $t('transactions.redecode_events.all') }}
                      </v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-menu>
              </v-col>
              <v-col>
                <div v-if="false">
                  <blockchain-account-selector
                    v-model="account"
                    :chains="['ETH']"
                    dense
                    :label="$tc('transactions.filter.account')"
                    outlined
                    no-padding
                    flat
                  />
                </div>
              </v-col>
            </v-row>
          </v-col>
          <v-col cols="12" md="6">
            <div v-if="false">
              <table-filter
                :matchers="matchers"
                @update:matches="updateFilterHandler($event)"
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
        :mobile-breakpoint="0"
        :item-class="item => (item.ignoredInAccounting ? 'darken-row' : '')"
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
                    {{ $t('transactions.actions.add_event') }}
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
        <template #body.prepend="{ headers }">
          <transaction-query-status :colspan="headers.length" />
          <upgrade-row
            v-if="showUpgradeRow"
            :limit="limit"
            :total="total"
            :colspan="headers.length"
            :label="$tc('transactions.label')"
          />
        </template>
      </data-table>
    </card>
    <big-dialog
      :display="openDialog"
      :title="dialogTitle"
      :primary-action="$tc('transactions.events.dialog.save')"
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
import {
  computed,
  defineComponent,
  Ref,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import Fragment from '@/components/helper/Fragment';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import {
  MatchedKeyword,
  SearchMatcher
} from '@/components/history/filtering/types';
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
import { setupSettings } from '@/composables/settings';
import i18n from '@/i18n';
import {
  EthTransaction,
  NewEthTransactionEvent,
  TransactionRequestPayload
} from '@/services/history/types';
import { useAssetInfoRetrieval } from '@/store/assets';
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
import { uniqueStrings } from '@/utils/data';
import { convertToTimestamp, getDateInputISOFormat } from '@/utils/date';
import TransactionQueryStatus from '@/views/history/transactions/TransactionQueryStatus.vue';

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

enum TransactionFilterKeys {
  START = 'start',
  END = 'end',
  ASSET = 'asset',
  PROTOCOL = 'protocol'
}

enum TransactionFilterValueKeys {
  START = 'fromTimestamp',
  END = 'toTimestamp',
  ASSET = 'asset',
  PROTOCOL = 'protocols'
}

export default defineComponent({
  name: 'TransactionContent',
  components: {
    TransactionQueryStatus,
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
    const { transactions, counterparties } = storeToRefs(transactionStore);

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
    const form = ref<TransactionEventFormInstance | null>(null);

    const getId = (item: EthTransactionEntry) => item.txHash;

    const selected: Ref<EthTransactionEntry[]> = ref([]);

    const { ignore } = setupIgnore(
      IgnoreActionType.ETH_TRANSACTIONS,
      selected,
      data,
      fetch,
      getId
    );

    const toggleIgnore = (item: EthTransactionEntry) => {
      set(selected, [item]);
      ignore(!item.ignoredInAccounting);
    };

    const addEvent = (item: EthTransactionEntry) => {
      set(selectedTransaction, item);
      set(
        dialogTitle,
        i18n.t('transactions.events.dialog.add.title').toString()
      );
      set(openDialog, true);
    };

    const editEventHandler = (event: EthTransactionEventEntry) => {
      set(editableItem, event);
      set(
        dialogTitle,
        i18n.t('transactions.events.dialog.edit.title').toString()
      );
      set(openDialog, true);
    };

    const promptForDelete = (
      item: EthTransactionEntry,
      event: EthTransactionEventEntry
    ) => {
      const canDelete = item.decodedEvents!.length > 1;

      if (canDelete) {
        set(
          confirmationTitle,
          i18n.t('transactions.events.confirmation.delete.title').toString()
        );
        set(
          confirmationMessage,
          i18n.t('transactions.events.confirmation.delete.message').toString()
        );
        set(
          confirmationPrimaryAction,
          i18n.t('transactions.events.confirmation.delete.action').toString()
        );
        set(eventToDelete, event);
      } else {
        set(
          confirmationTitle,
          i18n.t('transactions.events.confirmation.ignore.title').toString()
        );
        set(
          confirmationMessage,
          i18n.t('transactions.events.confirmation.ignore.message').toString()
        );
        set(
          confirmationPrimaryAction,
          i18n.t('transactions.events.confirmation.ignore.action').toString()
        );
        set(transactionToIgnore, item);
      }
    };

    const deleteEventHandler = async () => {
      if (get(transactionToIgnore)) {
        set(selected, [get(transactionToIgnore)]);
        ignore(true);
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
    const filters: Ref<MatchedKeyword<TransactionFilterValueKeys>> = ref({});

    const updatePayloadHandler = () => {
      let paginationOptions = {};
      const optionsVal = get(options);
      if (optionsVal) {
        set(options, {
          ...optionsVal,
          sortBy: optionsVal.sortBy.length > 0 ? [optionsVal.sortBy[0]] : [],
          sortDesc:
            optionsVal.sortDesc.length > 0 ? [optionsVal.sortDesc[0]] : []
        });

        const { itemsPerPage, page, sortBy, sortDesc } = get(options)!;
        const offset = (page - 1) * itemsPerPage;

        paginationOptions = {
          limit: itemsPerPage,
          offset,
          orderByAttribute: sortBy.length > 0 ? sortBy[0] : 'timestamp',
          ascending: !sortDesc[0]
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

      updateTransactionsPayload(payload);
    };

    const updatePaginationHandler = (newOptions: PaginationOptions | null) => {
      set(options, newOptions);
      updatePayloadHandler();
    };

    const updateFilterHandler = (
      newFilters: MatchedKeyword<TransactionFilterKeys>
    ) => {
      set(filters, newFilters);

      let newOptions = null;
      if (get(options)) {
        newOptions = {
          ...get(options)!,
          page: 1
        };
      }

      updatePaginationHandler(newOptions);
    };

    watch(account, () => {
      let newOptions = null;
      if (get(options)) {
        newOptions = {
          ...get(options)!,
          page: 1
        };
      }

      updatePaginationHandler(newOptions);
    });

    const loading = isSectionLoading(Section.TX);
    const eventTaskLoading = isTaskRunning(TaskType.TX_EVENTS);

    const { dateInputFormat } = setupSettings();
    const assetInfoRetrievalStore = useAssetInfoRetrieval();
    const { supportedAssets } = toRefs(assetInfoRetrievalStore);
    const { getAssetSymbol, getAssetIdentifierForSymbol } =
      assetInfoRetrievalStore;

    const availableAssets = computed<string[]>(() => {
      return get(supportedAssets)
        .map(value => getAssetSymbol(value.identifier))
        .filter(uniqueStrings);
    });

    const matchers = computed<
      SearchMatcher<TransactionFilterKeys, TransactionFilterValueKeys>[]
    >(() => [
      {
        key: TransactionFilterKeys.START,
        keyValue: TransactionFilterValueKeys.START,
        description: i18n.t('transactions.filter.start_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('transactions.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, get(dateInputFormat)))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, get(dateInputFormat)).toString()
      },
      {
        key: TransactionFilterKeys.END,
        keyValue: TransactionFilterValueKeys.END,
        description: i18n.t('transactions.filter.end_date').toString(),
        suggestions: () => [],
        hint: i18n
          .t('transactions.filter.date_hint', {
            format: getDateInputISOFormat(get(dateInputFormat))
          })
          .toString(),
        validate: value => {
          return (
            value.length > 0 &&
            !isNaN(convertToTimestamp(value, get(dateInputFormat)))
          );
        },
        transformer: (date: string) =>
          convertToTimestamp(date, get(dateInputFormat)).toString()
      },
      {
        key: TransactionFilterKeys.ASSET,
        keyValue: TransactionFilterValueKeys.ASSET,
        description: i18n.t('transactions.filter.asset').toString(),
        suggestions: () => get(availableAssets),
        validate: (asset: string) => get(availableAssets).includes(asset),
        transformer: (asset: string) => getAssetIdentifierForSymbol(asset) ?? ''
      },
      {
        key: TransactionFilterKeys.PROTOCOL,
        keyValue: TransactionFilterValueKeys.PROTOCOL,
        description: i18n.t('transactions.filter.protocol').toString(),
        multiple: true,
        suggestions: () => get(counterparties),
        validate: (protocol: string) => !!protocol
      }
    ]);

    return {
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
      matchers,
      updatePaginationHandler,
      updateFilterHandler,
      toggleIgnore,
      forceRedecodeEvents,
      redecodeEvents
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
