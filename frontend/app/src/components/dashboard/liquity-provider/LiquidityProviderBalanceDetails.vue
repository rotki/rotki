<script setup lang="ts">
import type { AssetBalanceWithPrice, XswapAsset } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';

withDefaults(
  defineProps<{
    assets: XswapAsset[];
    premiumOnly?: boolean;
  }>(),
  {
    premiumOnly: true,
  },
);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const tableHeaders = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => [
  {
    label: t('common.asset'),
    key: 'asset',
    cellClass: 'text-no-wrap',
  },
  {
    label: t('common.price', {
      symbol: get(currencySymbol),
    }),
    key: 'price',
    align: 'end',
    class: 'text-no-wrap',
  },
  {
    label: t('common.amount'),
    key: 'amount',
    align: 'end',
  },
  {
    label: t('common.value_in_symbol', {
      symbol: get(currencySymbol),
    }),
    key: 'usdValue',
    align: 'end',
    class: 'text-no-wrap',
  },
]);

const premium = usePremium();

const { assetPrice } = useBalancePricesStore();

function transformAssets(assets: XswapAsset[]): AssetBalanceWithPrice[] {
  return assets.map(item => ({
    asset: item.asset,
    price: item.usdPrice ?? get(assetPrice(item.asset)) ?? Zero,
    amount: item.userBalance.amount,
    usdValue: item.userBalance.usdValue,
  }));
}

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'usdValue',
  direction: 'desc' as const,
});
</script>

<template>
  <RuiDataTable
    v-if="premium || !premiumOnly"
    dense
    outlined
    :cols="tableHeaders"
    :sort="sort"
    :rows="transformAssets(assets)"
    row-attr="asset"
    class="bg-white dark:bg-[#1E1E1E] my-2"
  >
    <template #item.asset="{ row }">
      <AssetDetails
        opens-details
        :asset="row.asset"
      />
    </template>
    <template #item.price="{ row }">
      <AmountDisplay
        v-if="row.price && row.price.gte(0)"
        no-scramble
        show-currency="symbol"
        :price-asset="row.asset"
        :price-of-asset="row.price"
        :fiat-currency="currencySymbol"
        :value="row.price"
      />
      <span v-else>-</span>
    </template>
    <template #item.amount="{ row }">
      <AmountDisplay :value="row.amount" />
    </template>
    <template #item.usdValue="{ row }">
      <AmountDisplay
        show-currency="symbol"
        :amount="row.amount"
        :price-asset="row.asset"
        :price-of-asset="row.price"
        :fiat-currency="currencySymbol"
        :value="row.usdValue"
      />
    </template>
  </RuiDataTable>
  <RuiCard
    v-else
    dense
    variant="flat"
  >
    <div class="flex items-center gap-2 text-body-2">
      <PremiumLock />
      {{ t('uniswap.assets_non_premium') }}
    </div>
  </RuiCard>
</template>
