<template>
  <card outlined-body>
    <template #title>{{ $t('profit_loss_events.title') }}</template>
    <data-table
      :headers="tableHeaders"
      :items="items"
      single-expand
      :loading="loading || refreshing"
      :expanded.sync="expanded"
      :server-items-length="itemLength"
      :options.sync="options"
      sort-by="time"
    >
      <template #item.type="{ item }">
        <profit-loss-event-type :type="item.type" />
      </template>
      <template #item.location="{ item }">
        <location-display :identifier="item.location" />
      </template>
      <template #item.time="{ item }">
        <date-display :timestamp="item.timestamp" />
      </template>
      <template #item.free_amount="{ item }">
        <v-row no-gutters align="center" class="flex-nowrap">
          <v-col v-if="item.asset" cols="auto">
            <asset-link icon :asset="item.asset" class="mr-2">
              <asset-icon :identifier="item.asset" size="24px" />
            </asset-link>
          </v-col>
          <v-col>
            <div>
              <amount-display
                force-currency
                :value="item.freeAmount"
                :asset="item.asset ? item.asset : ''"
              />
            </div>
          </v-col>
        </v-row>
      </template>
      <template #item.taxable_amount="{ item }">
        <amount-display
          force-currency
          :value="item.taxableAmount"
          :asset="item.asset ? item.asset : ''"
        />
      </template>
      <template #item.price="{ item }">
        <amount-display
          force-currency
          :value="item.price"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template #item.pnl_taxable="{ item }">
        <amount-display
          pnl
          force-currency
          :value="item.pnlTaxable"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template #item.pnl_free="{ item }">
        <amount-display
          pnl
          force-currency
          :value="item.pnlFree"
          :fiat-currency="report.settings.profitCurrency"
        />
      </template>
      <template v-if="showUpgradeMessage" #body.prepend="{ headers }">
        <upgrade-row
          events
          :total="report.totalActions"
          :limit="report.processedActions"
          :time-end="report.lastProcessedTimestamp"
          :time-start="report.firstProcessedTimestamp"
          :colspan="headers.length"
          :label="$tc('profit_loss_events.title')"
        />
      </template>
      <template #item.notes="{ item }">
        <div class="py-4">
          <transaction-event-note
            v-if="isTransactionEvent(item)"
            :notes="item.notes"
            :amount="item.taxableAmount"
            :asset="item.asset"
          />
          <template v-else>{{ item.notes }}</template>
        </div>
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="item.costBasis"
          :expanded="expanded.includes(item)"
          @click="expanded = expanded.includes(item) ? [] : [item]"
        />
      </template>
      <template #expanded-item="{ headers, item }">
        <cost-basis-table
          :visible="!!item.costBasis"
          :currency="report.settings.profitCurrency"
          :colspan="headers.length"
          :cost-basis="item.costBasis"
        />
      </template>
    </data-table>
  </card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import TransactionEventNote from '@/components/history/transactions/TransactionEventNote.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import CostBasisTable from '@/components/profitloss/CostBasisTable.vue';
import ProfitLossEventType, {
  TRANSACTION_EVENT
} from '@/components/profitloss/ProfitLossEventType.vue';
import { useRoute } from '@/composables/common';
import { getPremium } from '@/composables/session';
import i18n from '@/i18n';
import { ProfitLossEvent, SelectedReport } from '@/types/reports';

const tableHeaders: DataTableHeader[] = [
  {
    text: i18n.t('profit_loss_events.headers.type').toString(),
    align: 'center',
    value: 'type',
    width: 110,
    sortable: false
  },
  {
    text: i18n.t('profit_loss_events.headers.location').toString(),
    value: 'location',
    width: '120px',
    align: 'center',
    sortable: false
  },
  {
    text: i18n.t('profit_loss_events.headers.tax_free_amount').toString(),
    align: 'end',
    value: 'free_amount',
    sortable: false
  },
  {
    text: i18n.t('profit_loss_events.headers.taxable_amount').toString(),
    align: 'end',
    value: 'taxable_amount',
    sortable: false
  },
  {
    text: i18n.t('profit_loss_events.headers.price').toString(),
    align: 'end',
    value: 'price',
    sortable: false
  },
  {
    text: i18n.t('profit_loss_events.headers.pnl_free').toString(),
    align: 'end',
    value: 'pnl_free',
    sortable: false
  },
  {
    text: i18n.t('profit_loss_events.headers.pnl_taxable').toString(),
    align: 'end',
    value: 'pnl_taxable',
    sortable: false
  },
  {
    text: i18n.t('profit_loss_events.headers.time').toString(),
    value: 'time',
    sortable: false
  },
  {
    text: i18n.t('profit_loss_events.headers.notes').toString(),
    value: 'notes',
    sortable: false
  },
  {
    text: i18n.t('profit_loss_events.headers.cost_basis').toString(),
    value: 'expand',
    align: 'end',
    sortable: false
  }
];

type PaginationOptions = {
  page: number;
  itemsPerPage: number;
  sortBy: any[];
  sortDesc: boolean[];
};

export default defineComponent({
  components: {
    TransactionEventNote,
    DataTable,
    ProfitLossEventType,
    UpgradeRow,
    CostBasisTable,
    RowExpander,
    DateDisplay,
    AmountDisplay
  },
  props: {
    loading: {
      required: false,
      type: Boolean,
      default: false
    },
    refreshing: {
      required: false,
      type: Boolean,
      default: false
    },
    report: {
      required: true,
      type: Object as PropType<SelectedReport>
    }
  },
  emits: ['update:page'],
  setup(props, { emit }) {
    const route = useRoute();
    const options = ref<PaginationOptions | null>(null);
    const expanded = ref([]);
    const { report } = toRefs(props);

    const items = computed(() => {
      return report.value.entries.map((value, index) => ({
        ...value,
        id: index
      }));
    });

    const itemLength = computed(() => {
      const { entriesFound, entriesLimit } = report.value;
      if (entriesLimit > 0 && entriesLimit <= entriesFound) {
        return entriesLimit;
      }
      return entriesFound;
    });

    const premium = getPremium();

    const showUpgradeMessage = computed(
      () =>
        !premium.value &&
        report.value.totalActions > report.value.processedActions
    );

    const updatePagination = async (options: PaginationOptions | null) => {
      if (!options) {
        return;
      }
      const { itemsPerPage, page } = options;

      const reportId = parseInt(route.value.params.id);

      emit('update:page', {
        reportId,
        limit: itemsPerPage,
        offset: itemsPerPage * (page - 1)
      });
    };

    const isTransactionEvent = (item: ProfitLossEvent) => {
      return item.type === TRANSACTION_EVENT;
    };

    watch(options, updatePagination);

    return {
      items,
      itemLength,
      options,
      expanded,
      showUpgradeMessage,
      isTransactionEvent,
      tableHeaders
    };
  }
});
</script>
