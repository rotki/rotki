<template>
  <v-row>
    <v-col>
      <v-card>
        <v-card-title>Events</v-card-title>
        <v-card-text>
          <v-data-table
            :headers="headers"
            :items="events"
            :footer-props="footerProps"
          >
            <template #item.time="{ item }">
              <date-display :timestamp="item.time" />
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
              <amount-display :value="item.paidInProfitCurrency" />
            </template>
            <template #item.paidInAsset="{ item }">
              <amount-display :value="item.paidInAsset" />
            </template>
            <template #item.taxableAmount="{ item }">
              <amount-display :value="item.taxableAmount" />
            </template>
            <template #item.taxableBoughtCostInProfitCurrency="{ item }">
              <amount-display :value="item.taxableBoughtCostInProfitCurrency" />
            </template>
            <template #item.receivedInAsset="{ item }">
              <amount-display :value="item.receivedInAsset" />
            </template>
            <template #item.taxableReceivedInProfitCurrency="{ item }">
              <amount-display :value="item.taxableReceivedInProfitCurrency" />
            </template>
            <template #item.receivedAsset="{ item }">
              {{ item.receivedAsset ? item.receivedAsset : '-' }}
            </template>
            <template #item.paidAsset="{ item }">
              {{ item.paidAsset ? item.paidAsset : '-' }}
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
import { mapGetters, mapState } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DateDisplay from '@/components/display/DateDisplay.vue';
import { footerProps } from '@/config/datatable.common';
import { EventEntry } from '@/model/trade-history-types';

@Component({
  components: {
    DateDisplay,
    AmountDisplay
  },
  computed: {
    ...mapState('reports', ['currency', 'events']),
    ...mapGetters('balances', ['exchangeRate'])
  }
})
export default class TaxReportEvents extends Vue {
  events!: EventEntry[];
  currency!: string;
  exchangeRate!: (currency: string) => number;

  headers = [
    { text: 'Type', value: 'type' },
    { text: 'Location', value: 'location' },
    { text: 'Paid in USD', value: 'paidInProfitCurrency', align: 'end' },
    { text: 'Paid Asset', value: 'paidAsset' },
    { text: 'Paid in Asset', value: 'paidInAsset', align: 'end' },
    { text: 'Taxable Amount', value: 'taxableAmount', align: 'end' },
    {
      text: 'Taxable Bought Cost in USD',
      value: 'taxableBoughtCostInProfitCurrency',
      align: 'end'
    },
    { text: 'Received Asset', value: 'receivedAsset' },
    { text: 'Received in Asset', value: 'receivedInAsset', align: 'end' },
    {
      text: 'Taxable Received in USD',
      value: 'taxableReceivedInProfitCurrency',
      align: 'end'
    },
    { text: 'Time', value: 'time' },
    { text: 'Virtual?', value: 'isVirtual', align: 'center' }
  ];

  footerProps = footerProps;
}
</script>
