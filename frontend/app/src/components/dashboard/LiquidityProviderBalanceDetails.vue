<template>
  <table-expand-container visible :colspan="span" :padded="false">
    <data-table
      v-if="premium || !premiumOnly"
      hide-default-footer
      :headers="tableHeaders"
      :items="transformAssets(assets)"
      sort-by="usdValue"
    >
      <template #item.asset="{ item }">
        <asset-details opens-details :asset="item.asset" />
      </template>
      <template #item.usdPrice="{ item }">
        <amount-display
          v-if="item.usdPrice && item.usdPrice.gte(0)"
          show-currency="symbol"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdPrice"
        />
        <span v-else>-</span>
      </template>
      <template #item.amount="{ item }">
        <amount-display :value="item.amount" />
      </template>
      <template #item.usdValue="{ item }">
        <amount-display
          show-currency="symbol"
          :amount="item.amount"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdValue"
        />
      </template>
    </data-table>
    <div v-else class="d-flex align-center">
      <v-avatar rounded :color="dark ? 'white' : 'grey lighten-3'">
        <v-icon>mdi-lock</v-icon>
      </v-avatar>
      <div class="ml-4">
        <i18n tag="div" path="uniswap.assets_non_premium">
          <base-external-link
            :text="tc('uniswap.premium')"
            :href="premiumURL"
          />
        </i18n>
      </div>
    </div>
  </table-expand-container>
</template>
<script setup lang="ts">
import { AssetBalanceWithPrice } from '@rotki/common';
import { XswapAsset } from '@rotki/common/lib/defi/xswap';
import { PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import { useTheme } from '@/composables/common';
import { usePremium } from '@/composables/premium';
import { useInterop } from '@/electron-interop';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Zero } from '@/utils/bignumbers';

defineProps({
  span: {
    type: Number,
    required: false,
    default: 1
  },
  assets: {
    required: true,
    type: Array as PropType<XswapAsset[]>
  },
  premiumOnly: {
    required: false,
    type: Boolean,
    default: true
  }
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { premiumURL } = useInterop();
const { tc } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: tc('common.asset'),
    value: 'asset',
    cellClass: 'text-no-wrap',
    sortable: false
  },
  {
    text: tc('common.price', 0, {
      symbol: get(currencySymbol)
    }),
    value: 'usdPrice',
    align: 'end',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: tc('common.amount'),
    value: 'amount',
    align: 'end',
    sortable: false
  },
  {
    text: tc('common.value_in_symbol', 0, {
      symbol: get(currencySymbol)
    }),
    value: 'usdValue',
    align: 'end',
    class: 'text-no-wrap',
    sortable: false
  }
]);

const { dark } = useTheme();
const premium = usePremium();

const { assetPrice } = useBalancePricesStore();

const transformAssets = (assets: XswapAsset[]): AssetBalanceWithPrice[] => {
  return assets.map(item => {
    return {
      asset: item.asset,
      usdPrice: item.usdPrice ?? get(assetPrice(item.asset)) ?? Zero,
      amount: item.userBalance.amount,
      usdValue: item.userBalance.usdValue
    };
  });
};
</script>
