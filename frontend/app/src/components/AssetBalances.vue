<script setup lang="ts">
import { type AssetBalanceWithPrice } from '@rotki/common';
import { type Ref } from 'vue';
import { some } from 'lodash-es';
import { type DataTableHeader } from '@/types/vuetify';
import { isEvmNativeToken } from '@/types/asset';

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

const { t } = useI18n();

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

const isExpanded = (asset: string) => some(get(expanded), { asset });

const expand = (item: AssetBalanceWithPrice) => {
  set(expanded, isExpanded(item.asset) ? [] : [item]);
};
</script>

<template>
  <DataTable
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
      <AssetDetails
        opens-details
        :asset="item.asset"
        :is-collection-parent="!!item.breakdown"
      />
    </template>
    <template #item.usdPrice="{ item }">
      <AmountDisplay
        :loading="!item.usdPrice || item.usdPrice.lt(0)"
        no-scramble
        show-currency="symbol"
        :price-asset="item.asset"
        :price-of-asset="item.usdPrice"
        fiat-currency="USD"
        :value="item.usdPrice"
      />
    </template>
    <template #item.amount="{ item }">
      <AmountDisplay :value="item.amount" />
    </template>
    <template #item.usdValue="{ item }">
      <AmountDisplay
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
      <RowAppend
        label-colspan="3"
        :label="t('common.total')"
        :is-mobile="isMobile"
        :right-patch-colspan="2"
      >
        <AmountDisplay
          fiat-currency="USD"
          show-currency="symbol"
          :value="total"
        />
      </RowAppend>
    </template>
    <template #expanded-item="{ item }">
      <TableExpandContainer visible :colspan="tableHeaders.length">
        <EvmNativeTokenBreakdown
          v-if="!hideBreakdown && isEvmNativeToken(item.asset)"
          blockchain-only
          :identifier="item.asset"
        />
        <AssetBalances
          v-else
          v-bind="props"
          hide-total
          :balances="item.breakdown ?? []"
        />
      </TableExpandContainer>
    </template>
    <template #item.expand="{ item }">
      <RowExpander
        v-if="
          item.breakdown || (!hideBreakdown && isEvmNativeToken(item.asset))
        "
        :expanded="isExpanded(item.asset)"
        @click="expand(item)"
      />
    </template>
  </DataTable>
</template>
