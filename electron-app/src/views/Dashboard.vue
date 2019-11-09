<template>
  <v-container>
    <v-row>
      <v-col>
        <h1 class="page-header">Dashboard</h1>
      </v-col>
    </v-row>

    <div class="dashboard__information-boxes">
      <exchange-box
        v-for="exchange in exchanges"
        :key="exchange.name"
        :name="exchange.name"
        :amount="exchange.total"
      ></exchange-box>
      <information-box
        v-if="!blockchainTotal.isZero()"
        id="blockchain_box"
        icon="fa-hdd-o"
        :amount="blockchainTotal"
      ></information-box>
      <information-box
        v-if="!fiatTotal.isZero()"
        id="banks_box"
        icon="fa-university"
        :amount="fiatTotal"
      ></information-box>
    </div>

    <v-row>
      <v-col cols="12">
        <h1 class="page-header">All Balances</h1>
      </v-col>
    </v-row>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-data-table
            :headers="headers"
            :items="aggregatedBalances"
            :search="search"
            sort-by="usdValue"
            sort-desc
          >
            <template #header.usdValue>
              {{ currency.ticker_symbol }} value
            </template>
            <template #item.asset="{ item }">
              <span class="dashboard__aggregate__asset">
                <crypto-icon
                  width="26px"
                  class="dashboard__aggregate__asset__icon"
                  :symbol="item.asset"
                ></crypto-icon>
                {{ item.asset }}
              </span>
            </template>
            <template #item.amount="{ item }">
              {{ item.amount | precision(floatingPrecision) }}
            </template>
            <template #item.usdValue="{ item }">
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
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import InformationBox from '@/components/dashboard/InformationBox.vue';
import { createNamespacedHelpers } from 'vuex';
import { ExchangeInfo } from '@/typing/types';
import ExchangeBox from '@/components/dashboard/ExchangeBox.vue';
import { Currency } from '@/model/currency';
import CryptoIcon from '@/components/CryptoIcon.vue';
import BigNumber from 'bignumber.js';
import { Zero } from '@/utils/bignumbers';
import { AssetBalance } from '@/model/blockchain-balances';

const { mapGetters: mapBalanceGetters } = createNamespacedHelpers('balances');
const { mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { ExchangeBox, InformationBox, CryptoIcon },
  computed: {
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapBalanceGetters([
      'exchangeRate',
      'exchanges',
      'aggregatedBalances',
      'fiatTotal',
      'blockchainTotal'
    ])
  }
})
export default class Dashboard extends Vue {
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
  exchanges!: ExchangeInfo;
  fiatTotal!: BigNumber;
  blockchainTotal!: BigNumber;

  aggregatedBalances!: AssetBalance[];

  get total(): BigNumber {
    return this.aggregatedBalances.reduce(
      (sum, asset) => sum.plus(asset.usdValue),
      Zero
    );
  }
  search: string = '';

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Amount', value: 'amount' },
    { text: 'Value', value: 'usdValue' },
    { text: '% of net Value', value: 'percentage', sortable: false }
  ];
}
</script>

<style scoped lang="scss">
.dashboard__aggregate__asset {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.dashboard__information-boxes > * {
  margin-top: 16px;
}

.dashboard__aggregate__asset__icon {
  margin-right: 8px;
}
</style>
