<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library';
import type { AssetIdentifierResolution } from '@/modules/assets/types';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import AssetDetails from '@/modules/assets/AssetDetails.vue';
import { useSetting } from '@/modules/settings/use-setting';
import HistoricalBalancesBuckets from '@/modules/statistics/historical-balances/components/HistoricalBalancesBuckets.vue';
import HistoricalBalanceValueCell from '@/modules/statistics/historical-balances/components/HistoricalBalanceValueCell.vue';
import { type HistoricalBalanceRow, sortRows } from '@/modules/statistics/historical-balances/historical-balances-view';

const { filtered = false, loading = false, rows } = defineProps<{
  rows: HistoricalBalanceRow[];
  loading?: boolean;
  /** A filter is narrowing the rows, so an empty table means nothing matched. */
  filtered?: boolean;
}>();

/** A collection row is headed by its main asset, so it is named as the collection. */
const COLLECTION_RESOLUTION: AssetIdentifierResolution = { isCollectionParent: true };

const { t } = useI18n({ useScope: 'global' });

const expanded = ref<HistoricalBalanceRow[]>([]);

const currencySymbol = useSetting('currencySymbol');

const sorted = computed<HistoricalBalanceRow[]>(() => sortRows(rows));

const cols = computed<DataTableColumn<HistoricalBalanceRow>[]>(() => [
  { cellClass: 'py-0', class: 'w-full', key: 'asset', label: t('common.asset') },
  { align: 'end', cellClass: 'py-0', class: 'text-no-wrap', key: 'locations', label: t('historical_balances.table.locations') },
  { align: 'end', cellClass: 'py-0', class: 'text-no-wrap', key: 'price', label: t('common.price_in_symbol', { symbol: get(currencySymbol) }) },
  { align: 'end', cellClass: 'py-0', key: 'amount', label: t('common.amount') },
  { align: 'end', cellClass: 'py-0', class: 'text-no-wrap', key: 'value', label: t('common.value_in_symbol', { symbol: get(currencySymbol) }) },
]);

function isCollection(row: HistoricalBalanceRow): boolean {
  return row.members.length > 1;
}

function isExpanded(asset: string): boolean {
  return get(expanded).some(row => row.asset === asset);
}

function toggle(row: HistoricalBalanceRow): void {
  set(expanded, isExpanded(row.asset) ? [] : [row]);
}
</script>

<template>
  <RuiDataTable
    :cols="cols"
    :rows="sorted"
    :loading="loading"
    :expanded="expanded"
    :empty="{ description: filtered ? t('historical_balances.empty_filtered') : t('historical_balances.empty') }"
    row-attr="asset"
    single-expand
    outlined
    dense
    data-testid="historical-balances-table"
  >
    <template #item.asset="{ row }">
      <AssetDetails
        :asset="row.asset"
        :resolution="isCollection(row) ? COLLECTION_RESOLUTION : undefined"
      />
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
      <div class="flex items-center justify-end gap-1">
        <RuiTooltip
          v-if="row.partial"
          :open-delay="400"
          :class-names="{ tooltip: 'max-w-[16rem]' }"
        >
          <template #activator>
            <RuiIcon
              name="lu-circle-alert"
              size="14"
              color="warning"
              data-testid="historical-balances-partial"
            />
          </template>
          {{ t('historical_balances.price.partial_hint') }}
        </RuiTooltip>
        <HistoricalBalanceValueCell
          :value="row.value"
          :status="row.priceStatus"
        />
      </div>
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
        :show-asset="isCollection(row)"
      />
    </template>
  </RuiDataTable>
</template>
