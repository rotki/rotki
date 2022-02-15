<template>
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
      <v-row>
        <v-col cols="12" md="6">
          <ignore-buttons
            :disabled="selected.length === 0 || loading"
            @ignore="ignore"
          />
          <div v-if="selected.length > 0" class="mt-2 ms-1">
            {{ $t('transactions.selected', { count: selected.length }) }}
            <v-btn small text @click="selected = []">
              {{ $t('transactions.clear_selection') }}
            </v-btn>
          </div>
        </v-col>
        <v-col cols="12" md="6">
          <div class="pb-sm-8">
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
      v-model="selected"
      :expanded="data"
      :headers="tableHeaders"
      :items="data"
      :loading="loading"
      :options="options"
      :server-items-length="itemLength"
      class="table"
      :single-select="false"
      :mobile-breakpoint="0"
      :item-class="test"
      show-select
      item-key="identifier"
      @update:options="updatePaginationHandler($event)"
    >
      <template #item.ignoredInAccounting="{ item, isMobile }">
        <div v-if="item.ignoredInAccounting">
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
          {{ $t('transaction_details.internal_transaction') }}
        </v-chip>
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
      <template #item.action="{ item }">
        <v-dialog width="600">
          <template #activator="{ on }">
            <v-btn small color="primary" text v-on="on">
              {{ $t('transaction_details.details') }}
              <v-icon small>mdi-chevron-right</v-icon>
            </v-btn>
          </template>

          <transaction-detail :transaction="item" />
        </v-dialog>
      </template>
      <template #expanded-item="{ headers, item }">
        <transaction-events :transaction="item" :colspan="headers.length" />
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
</template>

<script lang="ts">
import { GeneralAccount } from '@rotki/common/lib/account';
import { defineComponent, Ref, ref, watch } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
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
  TransactionRequestPayload
} from '@/services/history/types';
import { Section } from '@/store/const';
import { useTransactions } from '@/store/history';
import { EthTransactionEntry, IgnoreActionType } from '@/store/history/types';
import { Collection } from '@/types/collection';

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
    cellClass: 'pa-0'
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

export default defineComponent({
  name: 'TransactionContent',
  components: {
    TransactionDetail,
    BadgeDisplay,
    UpgradeRow,
    TransactionEvents,
    IgnoreButtons,
    BlockchainAccountSelector,
    RefreshButton
  },
  emits: ['fetch'],
  setup(_, { emit }) {
    const fetch = (refresh: boolean = false) => emit('fetch', refresh);

    const transactionStore = useTransactions();
    const { transactions } = storeToRefs(transactionStore);

    const { updateTransactionsPayload } = transactionStore;

    const { data, limit, found, total } =
      getCollectionData<EthTransactionEntry>(
        transactions as Ref<Collection<EthTransactionEntry>>
      );

    const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total);

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

    const getId = (item: EthTransactionEntry) => item.identifier;
    const selected: Ref<EthTransactionEntry[]> = ref([]);

    const test = (item: EthTransactionEntry) => {
      return item.ignoredInAccounting ? 'grey lighten-4' : '';
    };

    return {
      test,
      selected,
      account,
      tableHeaders,
      data,
      limit,
      found,
      total,
      itemLength,
      fetch,
      showUpgradeRow,
      loading: isSectionLoading(Section.TX),
      options,
      updatePaginationHandler,
      ...setupIgnore(
        IgnoreActionType.ETH_TRANSACTIONS,
        selected,
        data,
        fetch,
        getId
      )
    };
  }
});
</script>
