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
          fiat-currency="USD"
          tooltip
          :price-asset="item.asset"
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
          :fiat-currency="item.asset"
          :amount="item.amount"
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
            :text="$t('uniswap.premium')"
            :href="$interop.premiumURL"
          />
        </i18n>
      </div>
    </div>
  </table-expand-container>
</template>
<script lang="ts">
import { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import { XswapAsset } from '@rotki/common/lib/defi/xswap';
import { computed, defineComponent, PropType, Ref } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import { useTheme } from '@/composables/common';
import { getPremium } from '@/composables/session';
import i18nFn from '@/i18n';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Zero } from '@/utils/bignumbers';

const createTableHeaders = (currency: Ref<string>) => {
  return computed<DataTableHeader[]>(() => {
    return [
      {
        text: i18nFn.t('common.asset').toString(),
        value: 'asset',
        cellClass: 'text-no-wrap',
        sortable: false
      },
      {
        text: i18nFn
          .t('common.price', {
            symbol: get(currency)
          })
          .toString(),
        value: 'usdPrice',
        align: 'end',
        class: 'text-no-wrap',
        sortable: false
      },
      {
        text: i18nFn.t('common.amount').toString(),
        value: 'amount',
        align: 'end',
        sortable: false
      },
      {
        text: i18nFn
          .t('common.value_in_symbol', {
            symbol: get(currency)
          })
          .toString(),
        value: 'usdValue',
        align: 'end',
        class: 'text-no-wrap',
        sortable: false
      }
    ];
  });
};

export default defineComponent({
  name: 'LiquidityProviderBalanceDetails',
  components: { BaseExternalLink, TableExpandContainer },
  props: {
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
  },
  setup() {
    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

    const { dark } = useTheme();
    const premium = getPremium();

    const { prices } = storeToRefs(useBalancePricesStore());

    const transformAssets = (assets: XswapAsset[]): AssetBalanceWithPrice[] => {
      return assets.map(item => {
        return {
          asset: item.asset,
          usdPrice:
            item.usdPrice ?? (get(prices)[item.asset] as BigNumber) ?? Zero,
          amount: item.userBalance.amount,
          usdValue: item.userBalance.usdValue
        };
      });
    };

    return {
      dark,
      premium,
      transformAssets,
      tableHeaders: createTableHeaders(currencySymbol)
    };
  }
});
</script>
