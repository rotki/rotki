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
        blockchain
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
            class="dashboard__balances"
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
              <asset-details :asset="item.asset"></asset-details>
            </template>
            <template #item.amount="{ item }">
              <amount-display :value="item.amount"></amount-display>
            </template>
            <template #item.usdValue="{ item }">
              <amount-display fiat :value="item.usdValue"></amount-display>
            </template>
            <template #item.percentage="{ item }">
              {{ item.usdValue | percentage(total, floatingPrecision) }}
            </template>
            <template #no-results>
              <v-alert :value="true" color="error" icon="warning">
                Your search for "{{ search }}" found no results.
              </v-alert>
            </template>
            <template v-if="aggregatedBalances.length > 0" #body.append>
              <tr class="dashboard__balances__total">
                <td>Total</td>
                <td></td>
                <td>
                  {{
                    aggregatedBalances.map(val => val.usdValue)
                      | balanceSum
                      | calculatePrice(exchangeRate(currency.ticker_symbol))
                      | formatPrice(floatingPrecision)
                  }}
                </td>
              </tr>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import CryptoIcon from '@/components/CryptoIcon.vue';
import ExchangeBox from '@/components/dashboard/ExchangeBox.vue';
import InformationBox from '@/components/dashboard/InformationBox.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import { AssetBalance } from '@/model/blockchain-balances';
import { Currency } from '@/model/currency';
import { ExchangeInfo } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

const { mapGetters: mapBalanceGetters } = createNamespacedHelpers('balances');
const { mapGetters } = createNamespacedHelpers('session');

@Component({
  components: {
    AmountDisplay,
    AssetDetails,
    ExchangeBox,
    InformationBox,
    CryptoIcon
  },
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
    { text: 'Amount', value: 'amount', align: 'end' },
    { text: 'Value', value: 'usdValue', align: 'end' },
    {
      text: '% of net Value',
      value: 'percentage',
      align: 'end',
      sortable: false
    }
  ];
}
</script>

<style scoped lang="scss">
.dashboard {
  &__balances {
    &__total {
      font-weight: 500;
    }
  }
  &__information-boxes > * {
    margin-top: 16px;
  }
}
</style>
