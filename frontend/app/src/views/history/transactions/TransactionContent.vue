<template>
  <card class="mt-8" outlined-body>
    <template #title>
      <refresh-button
        :loading="refreshing"
        :tooltip="$t('transactions.refresh_tooltip')"
        @refresh="fetch(true)"
      />
      {{ $t('transactions.title') }}
    </template>
    <template #actions>
      <v-row>
        <v-col cols="12" md="6">
          <ignore-buttons
            :disabled="selected.length === 0 || loading || refreshing"
            @ignore="ignore"
          />
          <div v-if="selected.length > 0" class="mt-2 ms-1">
            {{ $t('transactions.selected', { count: selected.length }) }}
            <v-btn small text @click="setAllSelected(false)">
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
      class="table"
      :expanded.sync="expanded"
      :headers="tableHeaders"
      :items="transactions"
      :loading="refreshing"
      :options="options"
      :server-items-length="itemLength"
      item-key="identifier"
      show-expand
      single-expand
      @update:options="updatePaginationHandler($event)"
    >
      <template #header.selection>
        <v-simple-checkbox
          :ripple="false"
          :value="isAllSelected"
          color="primary"
          @input="setAllSelected($event)"
        />
      </template>
      <template #item.selection="{ item }">
        <v-simple-checkbox
          :ripple="false"
          color="primary"
          :value="isSelected(item.identifier)"
          @input="selectionChanged(item.identifier, $event)"
        />
      </template>
      <template #item.ignoredInAccounting="{ item }">
        <v-icon v-if="item.ignoredInAccounting">mdi-check</v-icon>
      </template>
      <template #item.txHash="{ item }">
        <hash-link :text="item.txHash" tx />
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
      <template #item.fromAddress="{ item }">
        <hash-link :text="item.fromAddress" />
      </template>
      <template #item.toAddress="{ item }">
        <hash-link v-if="item.toAddress" :text="item.toAddress" />
        <span v-else>-</span>
      </template>
      <template #item.timestamp="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
      <template #item.value="{ item }">
        <amount-display :value="toEth(item.value)" asset="ETH" />
      </template>
      <template #item.gasFee="{ item }">
        <amount-display :value="gasFee(item)" asset="ETH" />
      </template>
      <template #expanded-item="{ headers, item }">
        <transactions-details :transaction="item" :colspan="headers.length" />
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
import { BigNumber } from '@rotki/common';
import { GeneralAccount } from '@rotki/common/lib/account';
import { defineComponent, Ref, ref, watch } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import BlockchainAccountSelector from '@/components/helper/BlockchainAccountSelector.vue';
import RefreshButton from '@/components/helper/RefreshButton.vue';
import IgnoreButtons from '@/components/history/IgnoreButtons.vue';
import TransactionsDetails from '@/components/history/TransactionsDetails.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { setupStatusChecking } from '@/composables/common';
import { setupEntryLimit, setupTransactions } from '@/composables/history';
import i18n from '@/i18n';
import {
  EthTransaction,
  TransactionRequestPayload
} from '@/services/history/types';
import { Section } from '@/store/const';
import { EthTransactionEntry, IgnoreActionType } from '@/store/history/types';
import { toUnit, Unit } from '@/utils/calculation';
import { setupIgnore } from '@/views/history/composables/ignore';
import { setupSelectionMode } from '@/views/history/composables/selection';

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof EthTransaction)[];
  sortDesc: boolean[];
};

const tableHeaders: DataTableHeader[] = [
  {
    text: '',
    value: 'selection',
    sortable: false
  },
  {
    text: i18n.t('transactions.headers.txhash').toString(),
    value: 'txHash',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: i18n.t('transactions.headers.block').toString(),
    value: 'blockNumber',
    align: 'end',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: i18n.t('transactions.headers.timestamp').toString(),
    value: 'timestamp',
    class: 'text-no-wrap'
  },
  {
    text: i18n.t('transactions.headers.from_address').toString(),
    value: 'fromAddress',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: i18n.t('transactions.headers.to_address').toString(),
    value: 'toAddress',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: i18n.t('transactions.headers.value').toString(),
    value: 'value',
    align: 'end',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: i18n.t('transactions.headers.gas_fee').toString(),
    value: 'gasFee',
    align: 'end',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: i18n.t('transactions.headers.ignored_in_accounting').toString(),
    value: 'ignoredInAccounting',
    width: '15px',
    class: 'text-no-wrap',
    sortable: false
  },
  { text: '', value: 'data-table-expand', sortable: false }
];

export default defineComponent({
  name: 'TransactionContent',
  components: {
    UpgradeRow,
    TransactionsDetails,
    IgnoreButtons,
    BlockchainAccountSelector,
    RefreshButton
  },
  emits: ['fetch', 'update:payload'],
  setup(_, { emit }) {
    const fetch = (refresh: boolean = false) => emit('fetch', refresh);
    const updatePayload = (payload: Partial<TransactionRequestPayload>) =>
      emit('update:payload', payload);

    const { transactions, limit, found, total } = setupTransactions();

    const { itemLength, showUpgradeRow } = setupEntryLimit(limit, found, total);

    const { isSectionRefreshing, shouldShowLoadingScreen } =
      setupStatusChecking();

    const expanded: Ref<EthTransactionEntry[]> = ref([]);

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

      updatePayload(payload);
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

    const selectionMode = setupSelectionMode<EthTransactionEntry>(
      transactions,
      getId
    );

    const gasFee = (tx: EthTransaction) =>
      toUnit(tx.gasPrice.multipliedBy(tx.gasUsed), Unit.ETH);
    const toEth = (value: BigNumber) => toUnit(value, Unit.ETH);

    return {
      account,
      tableHeaders,
      transactions,
      limit,
      found,
      total,
      itemLength,
      fetch,
      showUpgradeRow,
      updatePayload,
      loading: shouldShowLoadingScreen(Section.TX),
      refreshing: isSectionRefreshing(Section.TX),
      expanded,
      options,
      gasFee,
      toEth,
      updatePaginationHandler,
      ...selectionMode,
      ...setupIgnore(
        IgnoreActionType.ETH_TRANSACTIONS,
        selectionMode.selected,
        transactions,
        fetch,
        getId
      )
    };
  }
});
</script>

<style scoped lang="scss">
.table {
  ::v-deep {
    tbody {
      tr {
        > td {
          padding-top: 16px !important;
          padding-bottom: 16px !important;
        }
      }
    }
  }
}
</style>
