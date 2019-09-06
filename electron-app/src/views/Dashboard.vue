<template>
  <v-container>
    <v-row>
      <v-col>
        <h1 class="page-header">Dashboard</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <exchange-box
          v-for="exchange in exchanges"
          :key="exchange.name"
          :name="exchange.name"
          :amount="exchange.total"
        ></exchange-box>
        <information-box
          v-if="false"
          id="blockchain_box"
          icon="fa-hdd-o"
          :amount="0"
        ></information-box>
        <information-box
          v-if="false"
          id="banks_box"
          icon="fa-university"
          :amount="0"
        ></information-box>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <h1 class="page-header">All Balances</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-data-table
          :headers="headers"
          :items="aggregatedBalances"
          :search="search"
        >
          <template #item.asset="{ item }">
            {{ item.asset }}
          </template>
          <template #item.amount="{ item }">
            {{ item.amount | precision(floatingPrecision) }}
          </template>
          <template #item.usd_value="{ item }">
            {{
              item.usdValue
                | calculatePrice(exchangeRate(currency.ticker_symbol))
                | formatPrice(floatingPrecision)
            }}
          </template>
          <template #item.percentage="{ item }">
            {{ item.usdValue | percentage(total, floatingPrecision) }}
          </template>
          <template #no-results>
            <v-alert :value="true" color="error" icon="warning">
              Your search for "{{ search }}" found no results.
            </v-alert>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import InformationBox from '@/components/InformationBox.vue';
import { createNamespacedHelpers } from 'vuex';
import { ExchangeInfo } from '@/typing/types';
import { AssetBalance } from '@/model/asset-balance';
import ExchangeBox from '@/components/dashboard/ExchangeBox.vue';
import { Currency } from '@/model/currency';

const mapBalanceGetters = createNamespacedHelpers('balances').mapGetters;
const { mapState, mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { ExchangeBox, InformationBox },
  computed: {
    ...mapState(['currency']),
    ...mapGetters(['floatingPrecision']),
    ...mapBalanceGetters(['exchangeRate']),
    ...mapBalanceGetters(['exchanges', 'aggregatedBalances'])
  }
})
export default class Dashboard extends Vue {
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
  exchanges!: ExchangeInfo;

  aggregatedBalances!: AssetBalance[];
  search: string = '';

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Amount', value: 'amount' },
    { text: 'Value', value: 'usdValue' },
    { text: '% of net Value', value: 'percentage' }
  ];
}
</script>

<style scoped></style>
