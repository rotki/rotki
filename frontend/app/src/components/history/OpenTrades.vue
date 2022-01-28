<template>
  <v-row>
    <v-col cols="12">
      <v-card>
        <v-card-title>
          {{ $t('open_trades.title') }}
        </v-card-title>
        <v-card-text>
          <data-table :items="data" :headers="headers" />
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>
<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import DataTable from '@/components/helper/DataTable.vue';
import i18n from '@/i18n';
import { Trade } from '@/services/history/types';

const headers: DataTableHeader[] = [
  {
    text: i18n.t('open_trades.header.location').toString(),
    value: 'location'
  },
  {
    text: i18n.t('open_trades.header.action').toString(),
    value: 'tradeType'
  },
  {
    text: i18n.t('open_trades.header.pair').toString(),
    value: 'pair',
    align: 'end'
  },
  {
    text: i18n.t('open_trades.header.rate').toString(),
    value: 'rate',
    align: 'end'
  },
  {
    text: i18n.t('open_trades.header.amount').toString(),
    value: 'amount',
    align: 'end'
  },
  {
    text: i18n.t('open_trades.header.fee').toString(),
    value: 'fee',
    align: 'end'
  },
  {
    text: i18n.t('open_trades.header.fee_currency').toString(),
    value: 'feeCurrency',
    align: 'end'
  }
];
export default defineComponent({
  name: 'OpenTrades',

  components: { DataTable },
  props: {
    data: {
      required: false,
      type: Array as PropType<Trade[]>,
      default: () => []
    }
  },
  setup() {
    return {
      headers
    };
  }
});
</script>
