<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useSetting } from '@/modules/settings/use-setting';
import HistoricalBalancesBuckets from '@/modules/statistics/historical-balances/components/HistoricalBalancesBuckets.vue';
import HistoricalBalanceValueCell from '@/modules/statistics/historical-balances/components/HistoricalBalanceValueCell.vue';
import { type HistoricalAssetRow, PriceStatus } from '@/modules/statistics/historical-balances/use-historical-balance-values';

const { loading = false, rows } = defineProps<{
  rows: HistoricalAssetRow[];
  loading?: boolean;
}>();

/** Where a row falls before its value is compared: priced rows first, spam last. */
const STATUS_RANK: Readonly<Record<PriceStatus, number>> = {
  [PriceStatus.PRICED]: 0,
  [PriceStatus.PENDING]: 1,
  [PriceStatus.MISSING]: 2,
  [PriceStatus.SPAM]: 3,
};

const { t } = useI18n({ useScope: 'global' });

const expanded = ref<HistoricalAssetRow[]>([]);

const currencySymbol = useSetting('currencySymbol');

/**
 * Priced rows first by value, then rows still loading, then those with no price, then spam; each
 * group without a value by amount. A price arriving moves its row up once rather than the whole
 * table reshuffling while prices load.
 */
const sorted = computed<HistoricalAssetRow[]>(() => [...rows].sort((a, b) => {
  const byStatus = STATUS_RANK[a.priceStatus] - STATUS_RANK[b.priceStatus];
  if (byStatus !== 0)
    return byStatus;
  if (a.value && b.value)
    return b.value.comparedTo(a.value) ?? 0;
  return b.amount.comparedTo(a.amount) ?? 0;
}));

const cols = computed<DataTableColumn<HistoricalAssetRow>[]>(() => [
  { cellClass: 'py-0', class: 'w-full', key: 'asset', label: t('common.asset') },
  { align: 'end', cellClass: 'py-0', class: 'text-no-wrap', key: 'locations', label: t('historical_balances.table.locations') },
  { align: 'end', cellClass: 'py-0', class: 'text-no-wrap', key: 'price', label: t('common.price_in_symbol', { symbol: get(currencySymbol) }) },
  { align: 'end', cellClass: 'py-0', key: 'amount', label: t('common.amount') },
  { align: 'end', cellClass: 'py-0', class: 'text-no-wrap', key: 'value', label: t('common.value_in_symbol', { symbol: get(currencySymbol) }) },
]);

function isExpanded(asset: string): boolean {
  return get(expanded).some(row => row.asset === asset);
}

function toggle(row: HistoricalAssetRow): void {
  set(expanded, isExpanded(row.asset) ? [] : [row]);
}
</script>

<template>
  <RuiDataTable
    :cols="cols"
    :rows="sorted"
    :loading="loading"
    :expanded="expanded"
    :empty="{ description: t('historical_balances.empty') }"
    row-attr="asset"
    single-expand
    outlined
    dense
    data-testid="historical-balances-table"
  >
    <template #item.asset="{ row }">
      <AssetDetails :asset="row.asset" />
    </template>
    <template #item.locations="{ row }">
      {{ row.buckets.length }}
    </template>
    <template #item.price="{ row }">
      <HistoricalBalanceValueCell
        :value="row.price"
        :status="row.priceStatus"
        :price-asset="row.asset"
        explain
      />
    </template>
    <template #item.amount="{ row }">
      <ValueDisplay :value="row.amount" />
    </template>
    <template #item.value="{ row }">
      <HistoricalBalanceValueCell
        :value="row.value"
        :status="row.priceStatus"
      />
    </template>
    <template #item.expand="{ row }">
      <RuiTableRowExpander
        :expanded="isExpanded(row.asset)"
        @click="toggle(row)"
      />
    </template>
    <template #expanded-item="{ row }">
      <HistoricalBalancesBuckets
        :buckets="row.buckets"
        :price="row.price"
        :price-status="row.priceStatus"
      />
    </template>
  </RuiDataTable>
</template>
