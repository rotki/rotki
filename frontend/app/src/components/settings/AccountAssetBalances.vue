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
            v-if="prices[item.asset]"
            tooltip
            show-currency="symbol"
            fiat-currency="USD"
            :price-asset="item.asset"
            :value="prices[item.asset]"
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

<script lang="ts">
import { AssetBalance } from '@rotki/common';
import { computed, defineComponent, PropType } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import i18n from '@/i18n';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';

export default defineComponent({
  name: 'AccountAssetBalances',
  components: { DataTable, AmountDisplay },
  props: {
    assets: { required: true, type: Array as PropType<AssetBalance[]> },
    title: { required: true, type: String }
  },
  setup() {
    const { prices } = storeToRefs(useBalancePricesStore());
    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

    const headers = computed<DataTableHeader[]>(() => [
      {
        text: i18n.t('common.asset').toString(),
        class: 'text-no-wrap',
        value: 'asset',
        cellClass: 'asset-info'
      },
      {
        text: i18n
          .t('common.price_in_symbol', {
            symbol: get(currencySymbol)
          })
          .toString(),
        class: 'text-no-wrap',
        align: 'end',
        value: 'price'
      },
      {
        text: i18n.t('common.amount').toString(),
        value: 'amount',
        class: 'text-no-wrap',
        cellClass: 'asset-divider',
        align: 'end'
      },
      {
        text: i18n
          .t('common.value_in_symbol', {
            symbol: get(currencySymbol)
          })
          .toString(),
        value: 'usdValue',
        align: 'end',
        class: 'text-no-wrap'
      }
    ]);

    return {
      currencySymbol,
      prices,
      headers
    };
  }
});
</script>

<style scoped lang="scss">
::v-deep {
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
