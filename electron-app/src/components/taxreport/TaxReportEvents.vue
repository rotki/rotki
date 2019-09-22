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
              {{ item.paidInProfitCurrency | formatPrice(floatingPrecision) }}
            </template>
            <template #item.paidInAsset="{ item }">
              {{ item.paidInAsset | formatPrice(floatingPrecision) }}
            </template>
            <template #item.taxableAmount="{ item }">
              {{ item.taxableAmount | formatPrice(floatingPrecision) }}
            </template>
            <template #item.taxableBoughtCostInProfitCurrency="{ item }">
              {{
                item.taxableBoughtCostInProfitCurrency
                  | formatPrice(floatingPrecision)
              }}
            </template>
            <template #item.receivedInAsset="{ item }">
              {{ item.receivedInAsset | formatPrice(floatingPrecision) }}
            </template>
            <template #item.taxableReceivedInProfitCurrency="{ item }">
              {{
                item.taxableReceivedInProfitCurrency
                  | formatPrice(floatingPrecision)
              }}
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
import { EventEntry } from '@/model/trade-history-types';

const { mapGetters } = createNamespacedHelpers('session');
const { mapState } = createNamespacedHelpers('reports');
const { mapGetters: mapBalanceGetters } = createNamespacedHelpers('balances');

@Component({
  computed: {
    ...mapState(['currency', 'events']),
    ...mapGetters(['floatingPrecision', 'dateDisplayFormat']),
    ...mapBalanceGetters(['exchangeRate'])
  }
})
export default class TaxReportEvents extends Vue {
  events!: EventEntry[];
  currency!: string;
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
