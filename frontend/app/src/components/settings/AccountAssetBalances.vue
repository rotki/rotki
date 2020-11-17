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
  </fragment>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import Fragment from '@/components/helper/Fragment';
import { footerProps } from '@/config/datatable.common';
import { AssetBalances } from '@/store/balances/types';

@Component({
  components: { Fragment, AmountDisplay },
  computed: {
    ...mapGetters('session', ['floatingPrecision', 'currencySymbol']),
    ...mapGetters('balances', ['exchangeRate'])
  }
})
export default class AccountAssetBalances extends Vue {
  readonly footerProps = footerProps;
  readonly headers = [
    { text: this.$tc('account_asset_balance.headers.asset'), value: 'asset' },
    {
      text: this.$tc('account_asset_balance.headers.amount'),
      value: 'amount',
      align: 'end'
    },
    {
      text: this.$tc('account_asset_balance.headers.value'),
      value: 'usdValue',
      align: 'end'
    }
  ];

  @Prop({ required: true, type: Array })
  assets!: AssetBalances[];
  @Prop({ required: true, type: String })
  title!: string;

  currencySymbol!: string;
  floatingPrecision!: number;
  exchangeRate!: (currency: string) => number;
}
</script>

<style scoped lang="scss">
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
