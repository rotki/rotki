<script setup lang="ts">
import { type AssetBalance } from '@rotki/common';
import { type PropType } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';

defineProps({
  assets: { required: true, type: Array as PropType<AssetBalance[]> },
  title: { required: true, type: String }
});

const { t } = useI18n();

const { assetPrice } = useBalancePricesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('common.asset').toString(),
    class: 'text-no-wrap',
    value: 'asset',
    width: '99%'
  },
  {
    text: t('common.price_in_symbol', {
      symbol: get(currencySymbol)
    }).toString(),
    class: 'text-no-wrap',
    align: 'end',
    value: 'price'
  },
  {
    text: t('common.amount').toString(),
    value: 'amount',
    class: 'text-no-wrap',
    align: 'end'
  },
  {
    text: t('common.value_in_symbol', {
      symbol: get(currencySymbol)
    }).toString(),
    value: 'usdValue',
    align: 'end',
    class: 'text-no-wrap'
  }
]);

const getPrice = (asset: string) => get(assetPrice(asset)) ?? Zero;
</script>

<template>
  <div class="py-4">
    <div class="text-h6 mb-4">{{ title }}</div>
    <VSheet outlined rounded>
      <DataTable
        :items="assets"
        :headers="headers"
        class="account-asset-balances__table"
        sort-by="usdValue"
      >
        <template #item.asset="{ item }">
          <AssetDetails opens-details :asset="item.asset" />
        </template>
        <template #item.price="{ item }">
          <AmountDisplay
            v-if="assetPrice(item.asset).value"
            tooltip
            show-currency="symbol"
            fiat-currency="USD"
            :price-asset="item.asset"
            :value="getPrice(item.asset)"
          />
          <div v-else>-</div>
        </template>
        <template #item.amount="{ item }">
          <AmountDisplay :value="item.amount" />
        </template>
        <template #item.usdValue="{ item }">
          <AmountDisplay
            fiat-currency="USD"
            :value="item.usdValue"
            show-currency="symbol"
          />
        </template>
      </DataTable>
    </VSheet>
  </div>
</template>

<style scoped lang="scss">
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
