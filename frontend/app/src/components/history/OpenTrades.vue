<template>
  <v-row>
    <v-col cols="12">
      <v-card>
        <v-card-title>
          {{ $t('open_trades.title') }}
        </v-card-title>
        <v-card-text>
          <v-data-table
            :items="data"
            :headers="headersOpen"
            :footer-props="footerProps"
          />
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { footerProps } from '@/config/datatable.common';
import { Trade } from '@/services/history/types';

@Component({})
export default class OpenTrades extends Vue {
  @Prop({})
  data!: Trade[];

  readonly headersOpen: DataTableHeader[] = [
    {
      text: this.$t('open_trades.header.location').toString(),
      value: 'location'
    },
    {
      text: this.$t('open_trades.header.action').toString(),
      value: 'tradeType'
    },
    {
      text: this.$t('open_trades.header.pair').toString(),
      value: 'pair',
      align: 'end'
    },
    {
      text: this.$t('open_trades.header.rate').toString(),
      value: 'rate',
      align: 'end'
    },
    {
      text: this.$t('open_trades.header.amount').toString(),
      value: 'amount',
      align: 'end'
    },
    {
      text: this.$t('open_trades.header.fee').toString(),
      value: 'fee',
      align: 'end'
    },
    {
      text: this.$t('open_trades.header.fee_currency').toString(),
      value: 'feeCurrency',
      align: 'end'
    }
  ];

  footerProps = footerProps;
}
</script>
