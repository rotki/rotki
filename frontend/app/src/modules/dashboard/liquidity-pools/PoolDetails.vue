<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { PoolAsset } from './types';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import PremiumLock from '@/components/premium/PremiumLock.vue';
import { usePremium } from '@/composables/premium';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { type AssetBalanceWithPrice, Zero } from '@rotki/common';

interface PoolDetailsProps {
  assets: PoolAsset[];
  premiumOnly?: boolean;
}

withDefaults(defineProps<PoolDetailsProps>(), {
  premiumOnly: true,
});

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { assetPrice } = useBalancePricesStore();
const premium = usePremium();
const { t } = useI18n();

const cols = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => [{
  cellClass: 'text-no-wrap',
  key: 'asset',
  label: t('common.asset'),
}, {
  align: 'end',
  class: 'text-no-wrap',
  key: 'usdPrice',
  label: t('common.price', {
    symbol: get(currencySymbol),
  }),
}, {
  align: 'end',
  key: 'amount',
  label: t('common.amount'),
}, {
  align: 'end',
  class: 'text-no-wrap',
  key: 'usdValue',
  label: t('common.value_in_symbol', {
    symbol: get(currencySymbol),
  }),
}]);

function transformAssets(assets: PoolAsset[]): AssetBalanceWithPrice[] {
  return assets.map(item => ({
    amount: item.userBalance.amount,
    asset: item.asset,
    usdPrice: item.usdPrice ?? get(assetPrice(item.asset)) ?? Zero,
    usdValue: item.userBalance.usdValue,
  }));
}
</script>

<template>
  <RuiDataTable
    v-if="premium || !premiumOnly"
    dense
    outlined
    :cols="cols"
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
    <template #item.usdPrice="{ row }">
      <AmountDisplay
        v-if="row.usdPrice && row.usdPrice.gte(0)"
        no-scramble
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
