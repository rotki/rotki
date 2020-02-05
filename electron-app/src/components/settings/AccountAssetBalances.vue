<template>
  <v-row class="account-asset-balances" align="center" justify="center">
    <v-col cols="12">
      <v-data-table
        :items="assets"
        :headers="headers"
        class="account-asset-balances__table"
        sort-by="usdValue"
        sort-desc
      >
        <template #header.usdValue>
          {{ currency.ticker_symbol }} value
        </template>
        <template #item.asset="{ item }">
          <span class="account-asset-balances__balance__asset">
            <crypto-icon
              width="26px"
              class="account-asset-balances__balance__asset__icon"
              :symbol="item.asset"
            ></crypto-icon>
            {{ item.asset }}
          </span>
        </template>
        <template #item.amount="{ item }">
          {{ item.amount | formatPrice(floatingPrecision) }}
        </template>
        <template #item.usdValue="{ item }">
          {{
            item.usdValue
              | calculatePrice(exchangeRate(currency.ticker_symbol))
              | formatPrice(floatingPrecision)
          }}
        </template>
      </v-data-table>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import CryptoIcon from '@/components/CryptoIcon.vue';
import { AssetBalances } from '@/model/blockchain-balances';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';

const { mapGetters } = createNamespacedHelpers('balances');
const { mapGetters: mapSessionGetters } = createNamespacedHelpers('session');
const { mapGetters: mapBalancesGetters } = createNamespacedHelpers('balances');

@Component({
  components: { CryptoIcon },
  computed: {
    ...mapGetters(['accountAssets']),
    ...mapSessionGetters(['floatingPrecision', 'currency']),
    ...mapBalancesGetters(['exchangeRate'])
  }
})
export default class AccountAssetBalances extends Vue {
  @Prop({ required: true })
  account!: string;
  currency!: Currency;
  accountAssets!: (account: string) => AssetBalances[];
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;

  headers = [
    { text: 'Asset', value: 'asset' },
    { text: 'Amount', value: 'amount' },
    { text: 'USD Value', value: 'usdValue' }
  ];

  get assets(): AssetBalances[] {
    return this.accountAssets(this.account);
  }
}
</script>

<style scoped lang="scss">
.account-asset-balances {
  background-color: #fafafa;
}

.account-asset-balances ::v-deep .v-data-table {
  background-color: #fafafa;
}

.account-asset-balances__table {
  margin-left: 12px;
  margin-right: 12px;
}

.account-asset-balances__balance__asset {
  display: flex;
  flex-direction: row;
  align-items: center;
}

.account-asset-balances__balance__asset__icon {
  margin-right: 8px;
}
</style>
