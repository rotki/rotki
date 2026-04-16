<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { PoolAsset } from './types';
import { type AssetBalanceWithPrice, Zero } from '@rotki/common';
import { AssetValueDisplay, FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useAssetSelectInfo } from '@/modules/assets/use-asset-select-info';
import { sortAssetBalances } from '@/modules/core/common/display/balances';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import PremiumLock from '@/modules/premium/PremiumLock.vue';
import { usePremium } from '@/modules/premium/use-premium';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

interface PoolDetailsProps {
  assets: PoolAsset[];
  premiumOnly?: boolean;
}

const { assets, premiumOnly = true } = defineProps<PoolDetailsProps>();

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'value',
  direction: 'desc' as const,
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { getAssetPrice } = usePriceUtils();
const { getAssetInfo } = useAssetSelectInfo();
const premium = usePremium();
const { t } = useI18n({ useScope: 'global' });

const cols = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => [{
  cellClass: 'text-no-wrap',
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, {
  align: 'end',
  class: 'text-no-wrap',
  key: 'price',
  label: t('common.price', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}, {
  align: 'end',
  key: 'amount',
  label: t('common.amount'),
  sortable: true,
}, {
  align: 'end',
  class: 'text-no-wrap',
  key: 'value',
  label: t('common.value_in_symbol', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}]);

useRememberTableSorting<AssetBalanceWithPrice>(TableId.POOL_LIQUIDITY_BALANCE_DETAIL, sort, cols);

const sorted = computed<AssetBalanceWithPrice[]>(() => {
  const transformed: AssetBalanceWithPrice[] = assets.map(item => ({
    amount: item.userBalance.amount,
    asset: item.asset,
    price: getAssetPrice(item.asset, Zero),
    value: item.userBalance.value,
  }));

  return sortAssetBalances(transformed, get(sort), getAssetInfo);
});
</script>

<template>
  <RuiDataTable
    v-if="premium || !premiumOnly"
    v-model:sort.external="sort"
    dense
    outlined
    :cols="cols"
    :rows="sorted"
    row-attr="asset"
    class="bg-white dark:bg-dark-elevated my-2"
  >
    <template #item.asset="{ row }">
      <AssetDetails :asset="row.asset" />
    </template>
    <template #item.price="{ row }">
      <FiatDisplay
        v-if="row.price && row.price.gte(0)"
        :value="row.price"
        :price-asset="row.asset"
      />
      <span v-else>-</span>
    </template>
    <template #item.amount="{ row }">
      <ValueDisplay :value="row.amount" />
    </template>
    <template #item.value="{ row }">
      <AssetValueDisplay
        :asset="row.asset"
        :amount="row.amount"
        :price="row.price"
        :value="row.value"
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
      {{ t('modules.dashboard.liquidity_pools.pool_details.premium_only') }}
    </div>
  </RuiCard>
</template>
