<script setup lang="ts">
import { type AssetBalanceWithPrice } from '@rotki/common';
import { type Ref } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { isEvmNativeToken } from '@/types/asset';

const { t } = useI18n();

const props = withDefaults(
  defineProps<{
    balances: AssetBalanceWithPrice[];
    loading?: boolean;
    hideTotal?: boolean;
    hideBreakdown?: boolean;
  }>(),
  {
    loading: false,
    hideTotal: false,
    hideBreakdown: false
  }
);

const { balances } = toRefs(props);
const expanded: Ref<AssetBalanceWithPrice[]> = ref([]);

const total = computed(() =>
  bigNumberSum(balances.value.map(({ usdValue }) => usdValue))
);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetInfo } = useAssetInfoRetrieval();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.asset').toString(),
    value: 'asset',
    class: 'text-no-wrap'
  },
  {
    text: t('common.price_in_symbol', {
      symbol: get(currencySymbol)
    }).toString(),
    value: 'usdPrice',
    align: 'end',
    class: 'text-no-wrap'
  },
  {
    text: t('common.amount').toString(),
    value: 'amount',
    align: 'end',
    width: '50%'
  },
  {
    text: t('common.value_in_symbol', {
      symbol: get(currencySymbol)
    }).toString(),
    value: 'usdValue',
    align: 'end',
    class: 'text-no-wrap'
  },
  {
    text: '',
    width: '48px',
    value: 'expand',
    sortable: false
  }
]);

const sortItems = getSortItems(asset => get(assetInfo(asset)));
</script>

<template>
  <data-table
    :headers="tableHeaders"
    :items="balances"
    :loading="loading"
    single-expand
    :expanded="expanded"
    :loading-text="t('asset_balances.loading')"
    :custom-sort="sortItems"
    sort-by="usdValue"
    item-key="asset"
  >
    <template #item.asset="{ item }">
      <asset-details
        opens-details
        :asset="item.asset"
        :is-collection-parent="!!item.breakdown"
      />
    </template>
    <template #item.usdPrice="{ item }">
      <amount-display
        v-if="item.usdPrice && item.usdPrice.gte(0)"
        no-scramble
        show-currency="symbol"
        :price-asset="item.asset"
        :price-of-asset="item.usdPrice"
        fiat-currency="USD"
        :value="item.usdPrice"
      />
      <div v-else class="d-flex justify-end">
        <v-skeleton-loader width="70" type="text" />
      </div>
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
    <template
      v-if="balances.length > 0 && !hideTotal"
      #body.append="{ isMobile }"
    >
      <row-append
        label-colspan="3"
        :label="t('common.total')"
        :is-mobile="isMobile"
      >
        <amount-display
          fiat-currency="USD"
          show-currency="symbol"
          :value="total"
        />
      </row-append>
    </template>
    <template #expanded-item="{ item }">
      <table-expand-container visible :colspan="tableHeaders.length">
        <evm-native-token-breakdown
          v-if="!hideBreakdown && isEvmNativeToken(item.asset)"
          blockchain-only
          :identifier="item.asset"
        />
        <asset-balances
          v-else
          v-bind="props"
          hide-total
          :balances="item.breakdown ?? []"
        />
      </table-expand-container>
    </template>
    <template #item.expand="{ item }">
      <row-expander
        v-if="
          item.breakdown || (!hideBreakdown && isEvmNativeToken(item.asset))
        "
        :expanded="expanded.includes(item)"
        @click="expanded = expanded.includes(item) ? [] : [item]"
      />
    </template>
  </data-table>
</template>
