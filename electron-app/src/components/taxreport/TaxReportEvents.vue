<template>
  <v-layout>
    <v-flex>
      <v-card>
        <v-card-title>Events</v-card-title>
        <v-card-text>
          <v-data-table :headers="headers" :items="events">
            <template #item.time="{ item }">
              {{ item.time | formatDate(dateDisplayFormat) }}
            </template>
          </v-data-table>
        </v-card-text>
      </v-card>
    </v-flex>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { EventEntry } from '@/model/trade-history-types';
import { Currency } from '@/model/currency';

const { mapState, mapGetters } = createNamespacedHelpers('session');
const mapReportsState = createNamespacedHelpers('reports').mapState;
const mapBalanceGetters = createNamespacedHelpers('balances').mapGetters;

@Component({
  computed: {
    ...mapReportsState(['events']),
    ...mapState(['currency']),
    ...mapGetters(['floatingPrecision', 'dateDisplayFormat']),
    ...mapBalanceGetters(['exchangeRate'])
  }
})
export default class TaxReportEvents extends Vue {
  events!: EventEntry[];
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
  dateDisplayFormat!: string;

  headers = [
    { text: 'Type', value: 'type' },
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
    { text: 'Virtual?', value: 'isVirtual' }
  ];
}
</script>

<style scoped></style>
