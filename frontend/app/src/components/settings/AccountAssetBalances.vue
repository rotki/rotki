<template>
  <v-row
    no-gutters
    class="account-asset-balances"
    align="center"
    justify="center"
  >
    <v-col cols="12">
      <v-data-table
        :items="assets"
        :headers="headers"
        class="account-asset-balances__table"
        sort-by="usdValue"
        sort-desc
        :footer-props="footerProps"
      >
        <template #header.usdValue>
          {{ currency.ticker_symbol }} value
        </template>
        <template #item.asset="{ item }">
          <asset-details :asset="item.asset" />
        </template>
        <template #item.amount="{ item }">
          <amount-display :value="item.amount" />
        </template>
        <template #item.usdValue="{ item }">
          <amount-display
            fiat-currency="USD"
            :value="item.usdValue"
            show-currency="symbol"
          />
        </template>
      </v-data-table>
    </v-col>
  </v-row>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { footerProps } from '@/config/datatable.common';
import { AssetBalances } from '@/model/blockchain-balances';
import { Currency } from '@/model/currency';

@Component({
  components: { AmountDisplay },
  computed: {
    ...mapGetters('balances', ['accountAssets']),
    ...mapGetters('session', ['floatingPrecision', 'currency']),
    ...mapGetters('balances', ['exchangeRate'])
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
    { text: 'Amount', value: 'amount', align: 'end' },
    { text: 'USD Value', value: 'usdValue', align: 'end' }
  ];

  footerProps = footerProps;

  get assets(): AssetBalances[] {
    return this.accountAssets(this.account);
  }
}
</script>

<style scoped lang="scss">
.account-asset-balances {
  background-color: #fafafa;

  ::v-deep {
    .v-data-table {
      background-color: #fafafa;
    }
  }

  &__table {
    margin-left: 12px;
    margin-right: 12px;
  }

  &__balance {
    &__asset {
      display: flex;
      flex-direction: row;
      align-items: center;

      &__icon {
        margin-right: 8px;
      }
    }
  }
}
</style>
