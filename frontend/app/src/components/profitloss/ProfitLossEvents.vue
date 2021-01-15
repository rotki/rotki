<template>
  <v-row>
    <v-col>
      <v-card>
        <v-card-title>{{ $t('profit_loss_events.title') }}</v-card-title>
        <v-card-text>
          <v-data-table
            :headers="headers"
            :items="events"
            sort-by="time"
            sort-desc
            :footer-props="footerProps"
          >
            <template #item.time="{ item }">
              <date-display :timestamp="item.time" />
            </template>
            <template #header.paidInProfitCurrency>
              {{ $t('profit_loss_events.headers.paid_in', { currency }) }}
            </template>
            <template #header.taxableBoughtCostInProfitCurrency>
              {{
                $t('profit_loss_events.headers.taxable_bought_cost_in', {
                  currency
                })
              }}
            </template>
            <template #header.taxableReceivedInProfitCurrency>
              {{
                $t('profit_loss_events.headers.taxable_received_in', {
                  currency
                })
              }}
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
              <v-icon v-if="item.isVirtual" color="success"> mdi-check </v-icon>
            </template>
          </v-data-table>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
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
export default class ProfitLossEvents extends Vue {
  events!: EventEntry[];
  currency!: string;
  exchangeRate!: (currency: string) => number;

  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('profit_loss_events.headers.type').toString(),
      value: 'type'
    },
    {
      text: this.$t('profit_loss_events.headers.location').toString(),
      value: 'location'
    },
    {
      text: this.$t('profit_loss_events.headers.paid_in', {
        currency: 'USD'
      }).toString(),
      value: 'paidInProfitCurrency',
      align: 'end'
    },
    {
      text: this.$t('profit_loss_events.headers.paid_asset').toString(),
      value: 'paidAsset'
    },
    {
      text: this.$t('profit_loss_events.headers.paid_in_asset').toString(),
      value: 'paidInAsset',
      align: 'end'
    },
    {
      text: this.$t('profit_loss_events.headers.taxable_amount').toString(),
      value: 'taxableAmount',
      align: 'end'
    },
    {
      text: this.$t('profit_loss_events.headers.taxable_bought_cost_in', {
        currency: 'USD'
      }).toString(),
      value: 'taxableBoughtCostInProfitCurrency',
      align: 'end'
    },
    {
      text: this.$t('profit_loss_events.headers.received_asset').toString(),
      value: 'receivedAsset'
    },
    {
      text: this.$t('profit_loss_events.headers.received_in_asset').toString(),
      value: 'receivedInAsset',
      align: 'end'
    },
    {
      text: this.$t('profit_loss_events.headers.taxable_received_in', {
        currency: 'USD'
      }).toString(),
      value: 'taxableReceivedInProfitCurrency',
      align: 'end'
    },
    {
      text: this.$t('profit_loss_events.headers.time').toString(),
      value: 'time'
    },
    {
      text: this.$t('profit_loss_events.headers.virtual').toString(),
      value: 'isVirtual',
      align: 'center'
    }
  ];

  readonly footerProps = footerProps;
}
</script>
