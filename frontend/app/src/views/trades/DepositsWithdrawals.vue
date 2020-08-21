<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            {{ $t('deposits_withdrawals.title') }}
          </v-card-title>
          <v-card-text>
            <v-data-table :headers="headers" />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';

@Component({})
export default class DepositsWithdrawals extends Vue {
  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('deposits_withdrawals.headers.location').toString(),
      value: 'location'
    },
    {
      text: this.$t('deposits_withdrawals.headers.action').toString(),
      value: 'movementCategory'
    },
    {
      text: this.$t('deposits_withdrawals.headers.asset').toString(),
      value: 'asset',
      align: 'end'
    },
    {
      text: this.$t('deposits_withdrawals.headers.amount').toString(),
      value: 'amount',
      align: 'end'
    },
    {
      text: this.$t('deposits_withdrawals.headers.usd_value').toString(),
      value: 'usdValue',
      align: 'end'
    },
    {
      text: this.$t('deposits_withdrawals.headers.fee').toString(),
      value: 'fee',
      align: 'end'
    },
    {
      text: this.$t('deposits_withdrawals.headers.fee_currency').toString(),
      value: 'feeCurrency',
      align: 'end'
    }
  ];
}
</script>
