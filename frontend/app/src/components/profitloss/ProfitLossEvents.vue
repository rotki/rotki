<template>
  <card outlined-body>
    <template #title>{{ $t('profit_loss_events.title') }}</template>
    <data-table
      :headers="tableHeaders"
      :items="indexedEvents"
      single-expand
      class="profit-loss-events__table"
      :expanded.sync="expanded"
      item-key="index"
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
          :total="processed"
          :limit="limit"
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
import { computed, defineComponent, ref } from '@vue/composition-api';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowExpander from '@/components/helper/RowExpander.vue';
import UpgradeRow from '@/components/history/UpgradeRow.vue';
import CostBasisTable from '@/components/profitloss/CostBasisTable.vue';
import ProfitLossEventType from '@/components/profitloss/ProfitLossEventType.vue';
import i18n from '@/i18n';
import { useReports } from '@/store/reports';

const getHeaders: () => DataTableHeader[] = () => [
  {
    text: i18n.t('profit_loss_events.headers.type').toString(),
    align: 'center',
    value: 'type',
    width: 110,
    class: 'profit-loss-events__table__header__type'
  },
  {
    text: i18n.t('profit_loss_events.headers.location').toString(),
    value: 'location',
    width: '120px',
    align: 'center',
    class: 'profit-loss-events__table__header__location'
  },
  {
    text: i18n
      .t('profit_loss_events.headers.paid_in', {
        currency: 'USD'
      })
      .toString(),
    value: 'paidInProfitCurrency',
    align: 'end'
  },
  {
    text: i18n.t('profit_loss_events.headers.paid_in_asset').toString(),
    value: 'paidInAsset',
    align: 'end'
  },
  {
    text: i18n.t('profit_loss_events.headers.taxable_amount').toString(),
    value: 'taxableAmount',
    align: 'end'
  },
  {
    text: i18n
      .t('profit_loss_events.headers.taxable_bought_cost_in', {
        currency: 'USD'
      })
      .toString(),
    value: 'taxableBoughtCostInProfitCurrency',
    align: 'end'
  },
  {
    text: i18n.t('profit_loss_events.headers.received_in_asset').toString(),
    value: 'receivedInAsset',
    align: 'end'
  },
  {
    text: i18n
      .t('profit_loss_events.headers.taxable_received_in', {
        currency: 'USD'
      })
      .toString(),
    value: 'taxableReceivedInProfitCurrency',
    align: 'end'
  },
  {
    text: i18n.t('profit_loss_events.headers.time').toString(),
    value: 'time'
  },
  {
    text: i18n.t('profit_loss_events.headers.virtual').toString(),
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
  setup() {
    const reportsStore = useReports();
    const { report, showUpgradeMessage, processed, limit } =
      storeToRefs(reportsStore);
    const expanded = ref([]);

    const indexedEvents = computed(() => {
      return report.value.events.map((value, index) => ({
        ...value,
        id: index
      }));
    });
    return {
      currency: 'USD',
      processed,
      limit,
      indexedEvents,
      showUpgradeMessage,
      expanded,
      tableHeaders: getHeaders()
    };
  }
});
</script>

<style lang="scss" scoped>
::v-deep {
  .profit-loss-events {
    &__table {
      &__header {
        &__type {
          span {
            padding-left: 16px;
          }
        }

        &__location {
          span {
            padding-left: 16px;
          }
        }
      }
    }
  }
}
</style>
