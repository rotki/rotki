<template>
  <div class="py-4">
    <div class="text-h6 mb-4">{{ title }}</div>
    <v-sheet outlined rounded>
      <data-table
        :items="assets"
        :headers="headers"
        class="account-asset-balances__table"
        sort-by="usdValue"
      >
        <template #item.asset="{ item }">
          <asset-details opens-details :asset="item.asset" />
        </template>
        <template #item.price="{ item }">
          <amount-display
            v-if="getAssetPrice(item.asset)"
            tooltip
            show-currency="symbol"
            fiat-currency="USD"
            :price-asset="item.asset"
            :value="getPrice(item.asset)"
          />
          <div v-else>-</div>
        </template>
        <template #item.amount="{ item }">
          <amount-display :value="item.amount" />
        </template>
        <template #item.usdValue="{ item }">
          <amount-display
            fiat-currency="USD"
            :value="item.usdValue"
            show-currency="symbol"
          />
        </template>
      </data-table>
    </v-sheet>
  </div>
</template>

<script setup lang="ts">
import { AssetBalance } from '@rotki/common';
import { PropType } from 'vue';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { Zero } from '@/utils/bignumbers';

defineProps({
  assets: { required: true, type: Array as PropType<AssetBalance[]> },
  title: { required: true, type: String }
});

const { t } = useI18n();
const { getAssetPrice } = useBalancePricesStore();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('common.asset').toString(),
    class: 'text-no-wrap',
    value: 'asset',
    cellClass: 'asset-info'
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
    cellClass: 'asset-divider',
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

const getPrice = (asset: string) => {
  return getAssetPrice(asset) ?? Zero;
};
</script>

<style scoped lang="scss">
:deep() {
  .asset-divider {
    width: 100%;

    @media (min-width: 2000px) {
      width: 50%;
    }
  }

  .asset-info {
    @media (min-width: 2000px) {
      width: 200px;
    }
  }
}

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
