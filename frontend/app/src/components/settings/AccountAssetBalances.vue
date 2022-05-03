<template>
  <div class="py-4">
    <div class="text-h6 mb-4">{{ title }}</div>
    <v-sheet outlined rounded>
      <data-table
        :items="assets"
        :headers="headers"
        class="account-asset-balances__table"
        sort-by="usdValue"
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
      </data-table>
    </v-sheet>
  </div>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import { usePrices } from '@/composables/balances';
import { setupGeneralSettings } from '@/composables/session';
import { CURRENCY_USD } from '@/data/currencies';
import i18n from '@/i18n';
import { AssetBalances } from '@/store/balances/types';

const headers: DataTableHeader[] = [
  {
    text: i18n.t('account_asset_balance.headers.asset').toString(),
    class: 'text-no-wrap',
    value: 'asset',
    cellClass: 'asset-info'
  },
  {
    text: i18n
      .t('account_asset_balance.headers.price', {
        symbol: CURRENCY_USD
      })
      .toString(),
    class: 'text-no-wrap',
    align: 'end',
    value: 'price'
  },
  {
    text: i18n.t('account_asset_balance.headers.amount').toString(),
    value: 'amount',
    class: 'text-no-wrap',
    cellClass: 'asset-divider',
    align: 'end'
  },
  {
    text: i18n.t('account_asset_balance.headers.value').toString(),
    value: 'usdValue',
    align: 'end',
    class: 'text-no-wrap'
  }
];

export default defineComponent({
  name: 'AccountAssetBalances',
  components: { DataTable, AmountDisplay },
  props: {
    assets: { required: true, type: Array as PropType<AssetBalances[]> },
    title: { required: true, type: String }
  },
  setup() {
    const { prices } = usePrices();
    const { currencySymbol } = setupGeneralSettings();

    return {
      currencySymbol,
      prices,
      headers
    };
  }
});
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
