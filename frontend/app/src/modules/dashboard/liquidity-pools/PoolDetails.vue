<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { PoolAsset } from './types';
import { type AssetBalanceWithPrice, Zero } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { usePremium } from '@/composables/premium';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { sortAssetBalances } from '@/utils/balances';

interface PoolDetailsProps {
  assets: PoolAsset[];
  premiumOnly?: boolean;
}

const props = withDefaults(defineProps<PoolDetailsProps>(), {
  premiumOnly: true,
});

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetPrice } = usePriceUtils();
const { assetInfo } = useAssetInfoRetrieval();
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
  key: 'usdPrice',
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
  key: 'usdValue',
  label: t('common.value_in_symbol', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}]);

useRememberTableSorting<AssetBalanceWithPrice>(TableId.POOL_LIQUIDITY_BALANCE_DETAIL, sort, cols);

const sorted = computed<AssetBalanceWithPrice[]>(() => {
  const transformed: AssetBalanceWithPrice[] = props.assets.map(item => ({
    amount: item.userBalance.amount,
    asset: item.asset,
    usdPrice: item.usdPrice ?? get(assetPrice(item.asset)) ?? Zero,
    usdValue: item.userBalance.usdValue,
  }));

  return sortAssetBalances(transformed, get(sort), assetInfo);
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
    class="bg-white dark:bg-[#1E1E1E] my-2"
  >
    <template #item.asset="{ row }">
      <AssetDetails :asset="row.asset" />
    </template>
    <template #item.usdPrice="{ row }">
      <AmountDisplay
        v-if="row.usdPrice && row.usdPrice.gte(0)"
        is-asset-price
        show-currency="symbol"
        :price-asset="row.asset"
        :price-of-asset="row.usdPrice"
        fiat-currency="USD"
        :value="row.usdPrice"
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
        :price-of-asset="row.usdPrice"
        fiat-currency="USD"
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
      {{ t('modules.dashboard.liquidity_pools.pool_details.premium_only') }}
    </div>
  </RuiCard>
</template>
