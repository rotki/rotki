<script setup lang="ts">
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import RowAppend from '@/components/helper/RowAppend.vue';
import BalanceTopProtocols from '@/modules/balances/protocols/BalanceTopProtocols.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';
import { sum } from '@/utils/balances';

interface AccountAssetBalancesProps {
  assets: AssetBalanceWithPrice[];
  title: string;
  flat?: boolean;
}

const props = withDefaults(defineProps<AccountAssetBalancesProps>(), {
  flat: false,
});

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'usdValue',
  direction: 'desc' as const,
});

const { t } = useI18n({ useScope: 'global' });
const { assets } = toRefs(props);

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const totalValue = computed<BigNumber>(() => sum(get(assets)));

const cols = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => [{
  cellClass: 'py-1',
  class: 'text-no-wrap w-full',
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, {
  cellClass: 'py-1',
  class: 'text-no-wrap w-full',
  key: 'perProtocol',
  label: t('common.location'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'py-1',
  class: 'text-no-wrap',
  key: 'usdPrice',
  label: t('common.price_in_symbol', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'py-1',
  class: 'text-no-wrap',
  key: 'amount',
  label: t('common.amount'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'py-1',
  class: 'text-no-wrap',
  key: 'usdValue',
  label: t('common.value_in_symbol', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}]);

useRememberTableSorting<AssetBalanceWithPrice>(TableId.ACCOUNT_ASSET_BALANCES, sort, cols);
</script>

<template>
  <RuiCard
    :no-padding="flat"
    :variant="flat ? 'flat' : 'outlined'"
    class="!rounded-xl my-2"
  >
    <template
      v-if="!flat && title"
      #header
    >
      {{ title }}
    </template>
    <RuiDataTable
      v-model:sort="sort"
      :rows="assets"
      :cols="cols"
      :empty="{ description: t('data_table.no_data') }"
      row-attr="asset"
      outlined
    >
      <template #item.asset="{ row }">
        <AssetDetails
          :asset="row.asset"
        />
      </template>
      <template #item.perProtocol="{ row }">
        <BalanceTopProtocols
          v-if="row.perProtocol"
          :protocols="row.perProtocol"
          :loading="!row.usdPrice || row.usdPrice.lt(0)"
          :asset="row.asset"
        />
      </template>
      <template #item.usdPrice="{ row }">
        <AmountDisplay
          :loading="!row.usdPrice || row.usdPrice.lt(0)"
          is-asset-price
          show-currency="symbol"
          fiat-currency="USD"
          :price-asset="row.asset"
          :price-of-asset="row.usdPrice"
          :value="row.usdPrice"
        />
      </template>
      <template #item.amount="{ row }">
        <AmountDisplay :value="row.amount" />
      </template>
      <template #item.usdValue="{ row }">
        <AmountDisplay
          fiat-currency="USD"
          :value="row.usdValue"
          show-currency="symbol"
        />
      </template>
      <template #body.append>
        <RowAppend
          label-colspan="3"
          :label="t('common.total')"
          class="[&>td]:p-4"
        >
          <AmountDisplay
            :fiat-currency="CURRENCY_USD"
            :value="totalValue"
            show-currency="symbol"
          />
        </RowAppend>
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
