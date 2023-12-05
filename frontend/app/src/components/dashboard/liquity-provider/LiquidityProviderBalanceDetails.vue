<script setup lang="ts">
import { type AssetBalanceWithPrice } from '@rotki/common';
import { type XswapAsset } from '@rotki/common/lib/defi/xswap';
import { type DataTableHeader } from '@/types/vuetify';

withDefaults(
  defineProps<{
    span?: number;
    assets: XswapAsset[];
    premiumOnly?: boolean;
  }>(),
  {
    span: 1,
    premiumOnly: true
  }
);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('common.asset'),
    value: 'asset',
    cellClass: 'text-no-wrap',
    sortable: false
  },
  {
    text: t('common.price', {
      symbol: get(currencySymbol)
    }),
    value: 'usdPrice',
    align: 'end',
    class: 'text-no-wrap',
    sortable: false
  },
  {
    text: t('common.amount'),
    value: 'amount',
    align: 'end',
    sortable: false
  },
  {
    text: t('common.value_in_symbol', {
      symbol: get(currencySymbol)
    }),
    value: 'usdValue',
    align: 'end',
    class: 'text-no-wrap',
    sortable: false
  }
]);

const premium = usePremium();

const { assetPrice } = useBalancePricesStore();

const transformAssets = (assets: XswapAsset[]): AssetBalanceWithPrice[] =>
  assets.map(item => ({
    asset: item.asset,
    usdPrice: item.usdPrice ?? get(assetPrice(item.asset)) ?? Zero,
    amount: item.userBalance.amount,
    usdValue: item.userBalance.usdValue
  }));
</script>

<template>
  <TableExpandContainer visible :colspan="span" no-padding>
    <DataTable
      v-if="premium || !premiumOnly"
      hide-default-footer
      flat
      :headers="tableHeaders"
      :items="transformAssets(assets)"
      sort-by="usdValue"
    >
      <template #item.asset="{ item }">
        <AssetDetails opens-details :asset="item.asset" />
      </template>
      <template #item.usdPrice="{ item }">
        <AmountDisplay
          v-if="item.usdPrice && item.usdPrice.gte(0)"
          no-scramble
          show-currency="symbol"
          :price-asset="item.asset"
          :price-of-asset="item.usdPrice"
          fiat-currency="USD"
          :value="item.usdPrice"
        />
        <span v-else>-</span>
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
    </DataTable>
    <RuiCard v-else dense variant="flat">
      <div class="flex items-center gap-2 text-body-2">
        <PremiumLock />
        {{ t('uniswap.assets_non_premium') }}
      </div>
    </RuiCard>
  </TableExpandContainer>
</template>
