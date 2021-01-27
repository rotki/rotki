<template>
  <fragment>
    <v-row class="account-asset-balances__header">
      <v-col class="text-h5 ms-6">{{ title }}</v-col>
    </v-row>
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
            {{
              $t('account_asset_balance.headers.value', {
                symbol: currencySymbol
              })
            }}
          </template>
          <template #header.price>
            {{
              $t('account_asset_balance.headers.price', {
                symbol: currencySymbol
              })
            }}
          </template>
          <template #item.asset="{ item }">
            <asset-details :asset="item.asset" />
          </template>
          <template #item.price="{ item }">
            <amount-display
              tooltip
              show-currency="symbol"
              fiat-currency="USD"
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
      </v-col>
    </v-row>
  </fragment>
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
    { text: this.$tc('account_asset_balance.headers.asset'), value: 'asset' },
    {
      text: this.$t('account_asset_balance.headers.price', {
        symbol: CURRENCY_USD
      }).toString(),
      value: 'price',
      width: '250px'
    },
    {
      text: this.$tc('account_asset_balance.headers.amount'),
      value: 'amount',
      width: '100%',
      align: 'end',
      cellClass: 'user-holding'
    },
    {
      text: this.$tc('account_asset_balance.headers.value'),
      value: 'usdValue',
      align: 'end',
      cellClass: 'user-holding user-asset-value'
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
  .user-holding {
    background-color: rgba(226, 226, 227, 0.2);
  }

  .user-asset-value {
    min-width: 150px;
  }
}

.account-asset-balances {
  background-color: #fafafa;

  &__header {
    background-color: #fafafa;
  }

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
