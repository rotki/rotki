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
        <date-display :timestamp="item.time" />
      </template>
      <template #item.paidInProfitCurrency="{ item }">
        <amount-display :value="item.paidInProfitCurrency" />
      </template>
      <template #item.paidInAsset="{ item }">
        <v-row
          no-gutters
          justify="space-between"
          align="center"
          class="flex-nowrap"
        >
          <v-col v-if="item.paidAsset" cols="auto">
            <asset-link icon :asset="item.paidAsset" class="pr-2">
              <asset-icon :identifier="item.paidAsset" size="24px" />
            </asset-link>
          </v-col>
          <v-col>
            <amount-display
              :value="item.paidInAsset"
              :asset="item.paidAsset ? item.paidAsset : ''"
            />
          </v-col>
        </v-row>
      </template>
      <template #item.taxableAmount="{ item }">
        <amount-display :value="item.taxableAmount" />
      </template>
      <template #item.taxableBoughtCostInProfitCurrency="{ item }">
        <amount-display :value="item.taxableBoughtCostInProfitCurrency" />
      </template>
      <template #item.receivedInAsset="{ item }">
        <v-row
          no-gutters
          justify="space-between"
          align="center"
          class="flex-nowrap"
        >
          <v-col v-if="item.receivedAsset" cols="auto">
            <asset-link icon :asset="item.receivedAsset" class="pr-2">
              <asset-icon
                :identifier="item.receivedAsset ? item.receivedAsset : ''"
                size="24px"
              />
            </asset-link>
          </v-col>
          <v-col>
            <amount-display
              :value="item.receivedInAsset"
              :asset="item.receivedAsset ? item.receivedAsset : ''"
            />
          </v-col>
        </v-row>
      </template>
      <template #item.taxableReceivedInProfitCurrency="{ item }">
        <amount-display :value="item.taxableReceivedInProfitCurrency" />
      </template>
      <template #item.isVirtual="{ item }">
        <v-icon v-if="item.isVirtual" color="success"> mdi-check</v-icon>
      </template>
      <template #expanded-item="{ headers, item }">
        <cost-basis-table
          :visible="!!item.costBasis"
          :colspan="headers.length"
          :cost-basis="item.costBasis"
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
          :label="$t('profit_loss_events.title')"
        />
      </template>
      <template #item.expand="{ item }">
        <row-expander
          v-if="item.costBasis"
          :expanded="expanded.includes(item)"
          @click="expanded = expanded.includes(item) ? [] : [item]"
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
  Ref,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import CostBasisTable from '@/components/profitloss/CostBasisTable.vue';
import ProfitLossEventType from '@/components/profitloss/ProfitLossEventType.vue';
import { useRoute } from '@/composables/common';
import { getPremium } from '@/composables/session';
import i18n from '@/i18n';
import { SelectedReport } from '@/types/reports';

const getHeaders: (report: Ref<SelectedReport>) => DataTableHeader[] =
  report => [
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
      text: i18n
        .t('profit_loss_events.headers.paid_in', {
          currency: report.value.currency
        })
        .toString(),
      sortable: false,
      value: 'paidInProfitCurrency',
      align: 'end'
    },
    {
      text: i18n.t('profit_loss_events.headers.paid_in_asset').toString(),
      sortable: false,
      value: 'paidInAsset',
      align: 'end'
    },
    {
      text: i18n.t('profit_loss_events.headers.taxable_amount').toString(),
      sortable: false,
      value: 'taxableAmount',
      align: 'end'
    },
    {
      text: i18n
        .t('profit_loss_events.headers.taxable_bought_cost_in', {
          currency: report.value.currency
        })
        .toString(),
      sortable: false,
      value: 'taxableBoughtCostInProfitCurrency',
      align: 'end'
    },
    {
      text: i18n.t('profit_loss_events.headers.received_in_asset').toString(),
      sortable: false,
      value: 'receivedInAsset',
      align: 'end'
    },
    {
      text: i18n
        .t('profit_loss_events.headers.taxable_received_in', {
          currency: report.value.currency
        })
        .toString(),
      sortable: false,
      value: 'taxableReceivedInProfitCurrency',
      align: 'end'
    },
    {
      text: i18n.t('profit_loss_events.headers.time').toString(),
      value: 'time'
    },
    {
      text: i18n.t('profit_loss_events.headers.virtual').toString(),
      sortable: false,
      value: 'isVirtual',
      align: 'center'
    },
    {
      text: '',
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

    watch(options, updatePagination);
    return {
      items,
      itemLength,
      options,
      expanded,
      showUpgradeMessage,
      tableHeaders: getHeaders(report)
    };
  }
});
</script>
