<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import { some } from 'es-toolkit/compat';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetSelectInfo } from '@/modules/assets/use-asset-select-info';
import { sortAssetBalances } from '@/modules/core/common/display/balances';
import HistoricalAssetRowDetails from '@/modules/history/balances/HistoricalAssetRowDetails.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

const { balances, loading, timestamp } = defineProps<{
  balances: AssetBalanceWithPrice[];
  loading?: boolean;
  timestamp?: number;
}>();

const { t } = useI18n({ useScope: 'global' });

const expanded = ref<AssetBalanceWithPrice[]>([]);

const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
  column: 'value',
  direction: 'desc' as const,
});

const { getAssetInfo } = useAssetSelectInfo();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { createKey, getIsPending } = useHistoricPriceCache();

function isPriceLoading(asset: string): boolean {
  if (!timestamp)
    return false;
  return getIsPending(createKey(asset, timestamp));
}

const isExpanded = (asset: string): boolean => some(get(expanded), { asset });

function shouldShowRowExpander(row: AssetBalanceWithPrice): boolean {
  return Boolean(row.breakdown);
}

function expand(item: AssetBalanceWithPrice): void {
  set(expanded, isExpanded(item.asset) ? [] : [item]);
}

const tableHeaders = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => [{
  cellClass: 'py-0',
  class: 'text-no-wrap w-full',
  key: 'asset',
  label: t('common.asset'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'py-0',
  key: 'price',
  label: t('common.price_in_symbol', {
    symbol: get(currencySymbol),
  }),
}, {
  align: 'end',
  cellClass: 'py-0',
  key: 'amount',
  label: t('common.amount'),
  sortable: true,
}, {
  align: 'end',
  cellClass: 'py-0',
  class: 'text-no-wrap',
  key: 'value',
  label: t('common.value_in_symbol', {
    symbol: get(currencySymbol),
  }),
  sortable: true,
}]);

const sorted = computed<AssetBalanceWithPrice[]>(() => sortAssetBalances([...balances], get(sort), getAssetInfo));
</script>

<template>
  <RuiDataTable
    v-model:sort.external="sort"
    :cols="tableHeaders"
    :rows="sorted"
    :loading="loading"
    :expanded="expanded"
    :loading-text="t('asset_balances.loading')"
    :empty="{ description: t('data_table.no_data') }"
    row-attr="asset"
    single-expand
    outlined
    dense
  >
    <template #item.asset="{ row }">
      <AssetDetails
        :asset="row.asset"
        :is-collection-parent="!!row.breakdown"
      />
    </template>
    <template #item.price="{ row }">
      <FiatDisplay
        :value="row.price"
        no-scramble
        :loading="isPriceLoading(row.asset)"
      />
    </template>
    <template #item.amount="{ row }">
      <ValueDisplay :value="row.amount" />
    </template>
    <template #item.value="{ row }">
      <FiatDisplay
        :value="row.value"
        :loading="isPriceLoading(row.asset)"
      />
    </template>
    <template #expanded-item="{ row }">
      <HistoricalAssetRowDetails
        :row="row"
        :loading="loading"
        :timestamp="timestamp"
      />
    </template>
    <template #item.expand="{ row }">
      <RuiTableRowExpander
        v-if="shouldShowRowExpander(row)"
        :expanded="isExpanded(row.asset)"
        @click="expand(row)"
      />
    </template>
  </RuiDataTable>
</template>
