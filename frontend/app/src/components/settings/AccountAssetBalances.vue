<template>
  <div class="py-4">
    <div class="text-h6 mb-4">{{ title }}</div>
    <v-sheet outlined rounded>
      <v-data-table
        :items="assets"
        :headers="headers"
        class="account-asset-balances__table"
        sort-by="usdValue"
        sort-desc
        must-sort
        :footer-props="footerProps"
      >
        <template #header.usdValue>
          <div class="text-no-wrap">
            {{
              $t('account_asset_balance.headers.value', {
                symbol: currencySymbol
              })
            }}
          </div>
        </template>
        <template #header.price>
          <div class="text-no-wrap">
            {{
              $t('account_asset_balance.headers.price', {
                symbol: currencySymbol
              })
            }}
          </div>
        </template>
        <template #item.asset="{ item }">
          <asset-details opens-details :asset="item.asset" />
        </template>
        <template #item.price="{ item }">
          <amount-display
            tooltip
            show-currency="symbol"
            fiat-currency="USD"
            :price-asset="item.asset"
            :value="prices[item.asset] ? prices[item.asset] : '-'"
          />
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
    </v-sheet>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import Fragment from '@/components/helper/Fragment';
import { footerProps } from '@/config/datatable.common';
import { CURRENCY_USD } from '@/data/currencies';
import { AssetBalances, AssetPrices } from '@/store/balances/types';

@Component({
  components: { Fragment, AmountDisplay },
  computed: {
    ...mapGetters('session', ['floatingPrecision', 'currencySymbol']),
    ...mapGetters('balances', ['exchangeRate']),
    ...mapState('balances', ['prices'])
  }
})
export default class AccountAssetBalances extends Vue {
  readonly footerProps = footerProps;
  readonly headers = [
    {
      text: this.$tc('account_asset_balance.headers.asset'),
      class: 'text-no-wrap',
      value: 'asset',
      cellClass: 'asset-info'
    },
    {
      text: this.$t('account_asset_balance.headers.price', {
        symbol: CURRENCY_USD
      }).toString(),
      class: 'text-no-wrap',
      align: 'end',
      value: 'price'
    },
    {
      text: this.$tc('account_asset_balance.headers.amount'),
      value: 'amount',
      class: 'text-no-wrap',
      cellClass: 'asset-divider',
      align: 'end'
    },
    {
      text: this.$tc('account_asset_balance.headers.value'),
      value: 'usdValue',
      align: 'end',
      class: 'text-no-wrap'
    }
  ];

  @Prop({ required: true, type: Array })
  assets!: AssetBalances[];
  @Prop({ required: true, type: String })
  title!: string;

  prices!: AssetPrices;
  currencySymbol!: string;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
}
</script>

<style scoped lang="scss">
::v-deep {
  .asset-divider {
    width: 100%;

    @media (min-width: 2000px) {
      width: 50%;
    }
  }

  .asset-info {
    @media (min-width: 2000px) {
      width: 200px;
    }
  }
}

.account-asset-balances {
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
