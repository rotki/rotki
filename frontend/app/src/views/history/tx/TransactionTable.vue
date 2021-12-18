<template>
  <data-table
    :class="$style.table"
    :expanded="expanded"
    :headers="tableHeaders"
    :items="txs"
    :options.sync="options"
    :server-items-length="itemLength"
    show-expand
    single-expand
  >
    <template #item.selection="{ item }">
      <v-simple-checkbox
        :ripple="false"
        color="primary"
        :value="isSelected(item.identifier)"
        @input="selectionChanged(item, $event)"
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
    <template v-if="limit <= total && limit > 0" #body.prepend="{ headers }">
      <upgrade-row
        :total="total"
        :limit="limit"
        :colspan="headers.length"
        :label="$t('transactions.label')"
      />
    </template>
    <template #expanded-item="{ headers, item }">
      <transactions-details :transaction="item" :colspan="headers.length" />
    </template>
  </data-table>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  Ref,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import TransactionsDetails from '@/components/history/TransactionsDetails.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import { getPremium } from '@/composables/session';
import i18n from '@/i18n';
import { EthTransaction } from '@/services/history/types';
import { EthTransactionEntry } from '@/store/history/types';
import { toUnit, Unit } from '@/utils/calculation';

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

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: (keyof EthTransaction)[];
  sortDesc: boolean[];
};
export default defineComponent({
  name: 'TransactionTable',
  components: { UpgradeRow, TransactionsDetails },
  props: {
    transactions: {
      required: true,
      type: Array as PropType<EthTransactionEntry[]>
    },
    limit: {
      required: true,
      type: Number
    },
    total: {
      required: true,
      type: Number
    },
    found: {
      required: true,
      type: Number
    },
    selected: {
      required: true,
      type: Array as PropType<string[]>
    },
    isSelected: {
      required: true,
      type: Function
    }
  },
  emits: ['update:selection', 'update:pagination'],
  setup(props, { emit }) {
    const expanded = ref([]);
    const options: Ref<PaginationOptions | null> = ref(null);
    const { transactions, found, limit } = toRefs(props);

    const txs = computed(() => {
      let id = 1;
      const txs = transactions.value;
      return txs.map(data => ({
        ...data,
        id: `${id++}`
      }));
    });

    const selectionChanged = (tx: EthTransaction, select: boolean) => {
      emit('update:selection', [tx.identifier, select]);
    };

    const updatePagination = (options: PaginationOptions | null) => {
      if (!options) {
        return;
      }
      const { itemsPerPage, page, sortBy, sortDesc } = options;
      emit('update:pagination', {
        page: page,
        sortBy: sortBy.length > 0 ? sortBy[0] : 'timestamp',
        ascending: !sortDesc[0],
        itemsPerPage
      });
    };

    watch(options, updatePagination);

    const premium = getPremium();
    const itemLength = computed(() => {
      const isPremium = premium.value;
      const totalFound = found.value;
      if (isPremium) {
        return totalFound;
      }

      const entryLimit = limit.value;
      return Math.min(totalFound, entryLimit);
    });

    return {
      expanded,
      tableHeaders,
      txs,
      options,
      itemLength,
      selectionChanged,
      gasFee: (tx: EthTransaction) =>
        toUnit(tx.gasPrice.multipliedBy(tx.gasUsed), Unit.ETH),
      toEth: (value: BigNumber) => toUnit(value, Unit.ETH)
    };
  }
});
</script>

<style module lang="scss">
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
