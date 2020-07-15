E<template>
  <v-card class="exchange-balances mt-8">
    <v-card-title>Exchange Balances</v-card-title>
    <v-card-text>
      <v-btn
        absolute
        fab
        top
        right
        dark
        color="primary"
        to="/settings/api-keys/exchanges"
      >
        <v-icon>
          fa fa-plus
        </v-icon>
      </v-btn>
      <v-row>
        <v-col cols="2">
          <v-tabs fixed-tabs vertical hide-slider optional>
            <v-tab
              v-for="(exchange, i) in connectedExchanges"
              :key="i"
              class="exchange-balances__tab my-3"
              active-class="exchange-balances__tab--active"
              :to="`/accounts-balances/exchange-balances/${exchange}`"
            >
              <v-img
                contain
                height="48"
                width="48"
                :title="exchange"
                :src="require(`@/assets/images/${exchange}.png`)"
                class="exchange-balances__tab__icon"
              />
              <div class="exchange-balances__tab__title d-block mt-2">
                {{ exchange }}
              </div>
              <div class="exchange-balances__tab__amount d-block">
                <amount-display
                  show-currency="symbol"
                  fiat-currency="USD"
                  :value="exchangeBalance(exchange)"
                ></amount-display>
              </div>
            </v-tab>
          </v-tabs>
        </v-col>
        <v-col cols="10">
          <asset-balances
            v-if="exchange"
            :balances="exchangeBalances(exchange)"
          ></asset-balances>
          <div v-else>
            Select an exchange to view asset details.
          </div>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Vue, Prop } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetBalances from '@/components/settings/AssetBalances.vue';
import { AssetBalance } from '@/model/blockchain-balances';
import { ExchangeInfo } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

const { mapState, mapGetters } = createNamespacedHelpers('balances');

@Component({
  components: {
    AssetBalances,
    AmountDisplay
  },
  computed: {
    ...mapState(['connectedExchanges']),
    ...mapGetters(['exchangeBalances', 'exchanges'])
  }
})
export default class ExchangeBalances extends Vue {
  @Prop({ required: false, default: '' })
  exchange!: string;

  connectedExchanges!: string[];
  exchanges!: ExchangeInfo;
  exchangeBalances!: (exchange: string) => AssetBalance[];

  exchangeBalance(exchange: string): BigNumber {
    const total: BigNumber = this.exchangeBalances(exchange).reduce(
      (sum, asset: AssetBalance) => sum.plus(asset.usdValue),
      Zero
    );

    return total;
  }
}
</script>

<style scoped lang="scss">
.exchange-balances {
  &__tab {
    display: flex;
    flex-direction: column;
    height: 100px !important;
    padding-top: 15px;
    padding-bottom: 15px;
    filter: grayscale(100%);
    color: var(--v-rotki-grey-base);

    &:hover {
      filter: grayscale(0);
    }

    &--active {
      filter: grayscale(0);
      border-radius: 8px;
      background-color: var(--v-rotki-light-grey-darken1);
      color: var(--v-secondary-base);
    }
  }
}
</style>
