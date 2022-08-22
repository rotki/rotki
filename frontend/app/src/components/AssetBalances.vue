<template>
  <data-table
    :headers="tableHeaders"
    :items="balances"
    :loading="loading"
    :loading-text="$t('asset_balances.loading')"
    :custom-sort="sortItems"
    sort-by="usdValue"
  >
    <template #item.asset="{ item }">
      <asset-details opens-details :asset="item.asset" />
    </template>
    <template #item.usdPrice="{ item }">
      <amount-display
        v-if="item.usdPrice && item.usdPrice.gte(0)"
        tooltip
        show-currency="symbol"
        fiat-currency="USD"
        :price-asset="item.asset"
        :value="item.usdPrice"
      />
      <span v-else>-</span>
    </template>
    <template #item.amount="{ item }">
      <amount-display :value="item.amount" />
    </template>
    <template #item.usdValue="{ item }">
      <amount-display
        show-currency="symbol"
        :fiat-currency="item.asset"
        :amount="item.amount"
        :value="item.usdValue"
      />
    </template>
    <template v-if="balances.length > 0" #body.append="{ isMobile }">
      <row-append
        label-colspan="3"
        :label="$t('common.total')"
        :is-mobile="isMobile"
      >
        <amount-display
          fiat-currency="USD"
          show-currency="symbol"
          :value="total"
        />
      </row-append>
    </template>
  </data-table>
</template>

<script lang="ts">
import { AssetBalanceWithPrice } from '@rotki/common';
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed, defineComponent, PropType, Ref, toRefs } from 'vue';
import { DataTableHeader } from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import DataTable from '@/components/helper/DataTable.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import { bigNumberSum } from '@/filters';
import i18n from '@/i18n';
import { useAssetInfoRetrieval } from '@/store/assets';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { getSortItems } from '@/utils/assets';

const tableHeaders = (symbol: Ref<string>) => {
  return computed<DataTableHeader[]>(() => {
    return [
      {
        text: i18n.t('common.asset').toString(),
        value: 'asset',
        class: 'text-no-wrap'
      },
      {
        text: i18n
          .t('common.price_in_symbol', { symbol: get(symbol) })
          .toString(),
        value: 'usdPrice',
        align: 'end',
        class: 'text-no-wrap'
      },
      {
        text: i18n.t('common.amount').toString(),
        value: 'amount',
        align: 'end',
        width: '99%'
      },
      {
        text: i18n
          .t('common.value_in_symbol', { symbol: get(symbol) })
          .toString(),
        value: 'usdValue',
        align: 'end',
        class: 'text-no-wrap'
      }
    ];
  });
};

const AssetBalancesTable = defineComponent({
  name: 'AssetBalancesTable',
  components: { RowAppend, DataTable, AmountDisplay },
  props: {
    balances: {
      required: true,
      type: Array as PropType<AssetBalanceWithPrice[]>
    },
    loading: {
      required: false,
      type: Boolean,
      default: false
    }
  },
  setup(props) {
    const { balances } = toRefs(props);
    const total = computed(() => {
      return bigNumberSum(balances.value.map(({ usdValue }) => usdValue));
    });

    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
    const { getAssetInfo } = useAssetInfoRetrieval();

    return {
      total,
      tableHeaders: tableHeaders(currencySymbol),
      sortItems: getSortItems(getAssetInfo),
      currency: currencySymbol
    };
  }
});

export default AssetBalancesTable;
</script>
