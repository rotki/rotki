<template>
  <v-row>
    <v-col>
      <v-card>
        <v-card-title>Events</v-card-title>
        <v-card-text>
          <v-data-table :headers="headers" :items="events">
            <template #item.time="{ item }">
              {{ item.time | formatDate(dateDisplayFormat) }}
            </template>
            <template #header.paidInProfitCurrency>
              Paid in {{ currency }}
            </template>
            <template #header.taxableBoughtCostInProfitCurrency>
              Taxable Bought Cost in {{ currency }}
            </template>
            <template #header.taxableReceivedInProfitCurrency>
              Taxable Received in {{ currency }}
            </template>
            <template #item.paidInProfitCurrency="{ item }">
              <amount-display
                :amount="item.paidInProfitCurrency"
              ></amount-display>
            </template>
            <template #item.paidInAsset="{ item }">
              <amount-display :amount="item.paidInAsset"></amount-display>
            </template>
            <template #item.taxableAmount="{ item }">
              <amount-display :amount="item.taxableAmount"></amount-display>
            </template>
            <template #item.taxableBoughtCostInProfitCurrency="{ item }">
              <amount-display
                :amount="item.taxableBoughtCostInProfitCurrency"
              ></amount-display>
            </template>
            <template #item.receivedInAsset="{ item }">
              <amount-display :amount="item.receivedInAsset"></amount-display>
            </template>
            <template #item.taxableReceivedInProfitCurrency="{ item }">
              <amount-display
                :amount="item.taxableReceivedInProfitCurrency"
              ></amount-display>
            </template>
            <template #item.isVirtual="{ item }">
              <v-icon v-if="item.isVirtual" color="success">
                fa-check
              </v-icon>
            </template>
          </v-data-table>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { EventEntry } from '@/model/trade-history-types';

const { mapGetters } = createNamespacedHelpers('session');
const { mapState } = createNamespacedHelpers('reports');
const { mapGetters: mapBalanceGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AmountDisplay
  },
  computed: {
    ...mapState(['currency', 'events']),
    ...mapGetters([
      'floatingPrecision',
      'dateDisplayFormat',
      'amountDisplayFormat'
    ]),
    ...mapBalanceGetters(['exchangeRate'])
  }
})
export default class TaxReportEvents extends Vue {
  events!: EventEntry[];
  currency!: string;
  floatingPrecision!: number;
  amountDisplayFormat!: string;
  exchangeRate!: (currency: string) => number;
  dateDisplayFormat!: string;

  headers = [
    { text: 'Type', value: 'type' },
    { text: 'Location', value: 'location' },
    { text: 'Paid in USD', value: 'paidInProfitCurrency' },
    { text: 'Paid Asset', value: 'paidAsset' },
    { text: 'Paid in Asset', value: 'paidInAsset' },
    { text: 'Taxable Amount', value: 'taxableAmount' },
    {
      text: 'Taxable Bought Cost in USD',
      value: 'taxableBoughtCostInProfitCurrency'
    },
    { text: 'Received Asset', value: 'receivedAsset' },
    { text: 'Received in Asset', value: 'receivedInAsset' },
    {
      text: 'Taxable Received in USD',
      value: 'taxableReceivedInProfitCurrency'
    },
    { text: 'Time', value: 'time' },
    { text: 'Virtual?', value: 'isVirtual', align: 'center' }
  ];
}
</script>

<style scoped></style>
