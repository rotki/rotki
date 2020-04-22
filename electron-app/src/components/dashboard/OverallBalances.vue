<template>
  <v-card class="overall-balances-box">
    <v-row>
      <v-col cols="3">
        <div class="overall-balances-box__balance">
          <span class="overall-balances-box__amount__number">
            {{
              total
                | calculatePrice(exchangeRate(currency.ticker_symbol))
                | formatPrice(floatingPrecision)
            }}
          </span>
          <span class="overall-balances-box__currency__symbol">
            {{ currency.unicode_symbol }}
          </span>
        </div>
        <div class="overall-balances-box__balance__change">
          <span
            style="
              background-color: #21ce99;
              color: #fff;
              padding: 0.25em;
              border-radius: 0.5em;
            "
          >
            ▼ XXX.XX {{ currency.unicode_symbol }}
          </span>
          <br />
          <span
            style="
              background-color: #f45431;
              color: #fff;
              padding: 0.25em;
              border-radius: 0.5em;
            "
          >
            ▲ XXX.XX {{ currency.unicode_symbol }}
          </span>
        </div>
        <div class="overall-balances-box__timeframe">
          <ul>
            <li class="overall-balances-box__timeframe__selected">All</li>
            <li>1D</li>
            <li style="text-decoration: line-through;">1W</li>
            <li style="text-decoration: line-through;">1M</li>
          </ul>
        </div>
      </v-col>
      <v-col cols="9">
        <div>
          GRAPH GOES HERE
        </div>
      </v-col>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';

import { AssetBalance } from '@/model/blockchain-balances';
import { Currency } from '@/model/currency';
import { Zero } from '@/utils/bignumbers';

const { mapGetters } = createNamespacedHelpers('session');
const { mapGetters: mapBalanceGetters } = createNamespacedHelpers('balances');

@Component({
  computed: {
    ...mapGetters(['floatingPrecision', 'currency']),
    ...mapBalanceGetters(['exchangeRate', 'aggregatedBalances'])
  }
})
export default class ExchangeBox extends Vue {
  currency!: Currency;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
  aggregatedBalances!: AssetBalance[];

  get total(): BigNumber {
    return this.aggregatedBalances.reduce(
      (sum, asset) => sum.plus(asset.usdValue),
      Zero
    );
  }
}
</script>
<style scoped lang="scss">
.overall-balances-box {
  padding-left: 12px;
  padding-right: 12px;
}

.overall-balances-box__balance {
  display: flex;
  justify-content: center;
  align-items: baseline;
}

.overall-balances-box__balance__change {
  display: flex;
  justify-content: center;
  align-items: baseline;
  margin-bottom: 1em;
}

.overall-balances-box__timeframe ul {
  display: flex;
  justify-content: center;
  padding: 0;
  font-size: 0.9em;
}

.overall-balances-box__timeframe ul li {
  display: inline;
  margin-left: 0.2em;
  margin-right: 0.2em;
  padding-left: 0.5em;
  padding-right: 0.5em;
  border-radius: 0.8em;
}

.overall-balances-box__timeframe__selected {
  background-color: #7e4a3b;
  color: white;
}

.overall-balances-box__currency__symbol {
  font-size: 2.2em;
}

.overall-balances-box__icon {
  margin-left: 8px;
  width: 45px;
  filter: grayscale(100%);
}

.overall-balances-box__icon--inverted {
  margin-left: 8px;
  width: 45px;
  filter: grayscale(100%) invert(100%);
}

.overall-balances-box__amount {
  color: white;
}

.overall-balances-box__amount__number {
  font-size: 3.1em;
}
</style>
